"""
Pipeline 编排服务 - 步骤 2.10

整合6个处理步骤（实际5个，步骤5岗位匹配暂跳），实现完整的简历处理流程：
  步骤1: 文档解析 (ParserService)
  步骤2: LLM结构化抽取 (ExtractorService)
  步骤3: 翻译+脱敏 (TranslatorService + AnonymizerService)
  步骤4: 约束性摘要 (SummarizationService)
  步骤5: [跳过] 岗位匹配评估 (待后续开发)
  步骤6: PPT模板填充 (SmartFillerService)

支持实时进度跟踪和异步任务处理
"""

import os
import re
import time
import uuid
import asyncio
import threading
import urllib.parse
import logging
from datetime import datetime
from typing import Optional, Dict

from app.schemas.resume import ResumeData
from app.services.cv_gender_confirmation import GenderConfirmation
from app.services.parser_service import ParserService
from app.services.extractor_service import ExtractorService
from app.services.translator_service import (
    TranslatorService, TranslationQualityError, translation_repair_observer,
)
from app.services.anonymizer_service import AnonymizerService
from app.services.summarization_service import SummarizationService
from app.services.smart_filler_service import SmartFillerService
from app.services.pptx_validator import validate_pptx
from app.core.config import settings


logger = logging.getLogger(__name__)


# ── 上传目录配置 ─────────────────────────────────────────
UPLOAD_DIR = str(settings.upload_path)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── 管道步骤定义 ─────────────────────────────────────────
PIPELINE_STEPS = [
    {"index": 1, "name": "文档解析", "key": "parsing"},
    {"index": 2, "name": "LLM结构化抽取", "key": "extracting"},
    {"index": 3, "name": "翻译+脱敏", "key": "transforming"},
    {"index": 4, "name": "约束性摘要", "key": "summarizing"},
    {"index": 5, "name": "岗位匹配评估", "key": "matching"},  # 跳过
    {"index": 6, "name": "PPT模板填充", "key": "filling"},
]

ACTIVE_STEPS = [s for s in PIPELINE_STEPS if s["key"] != "matching"]  # 5个有效步骤


class TaskInfo:
    """内存中的任务状态追踪对象"""

    def __init__(self, task_id: str, file_id: str, template_type: str,
                 target_language: str, job_position: str, template_language: str,
                 department: str = ""):
        self.task_id = task_id
        self.status = "pending"  # pending/processing/completed/failed
        self.progress = 0
        self.current_step = ""
        self.step_index = 0
        self.file_id = file_id
        self.template_type = template_type
        self.target_language = target_language
        self.job_position = job_position
        self.department = department
        self.template_language = template_language
        self.resume_data: Optional[dict] = None
        self.raw_text: Optional[str] = None
        self.gender_confirmation = GenderConfirmation()
        self.output_path: Optional[str] = None
        self.pdf_path: Optional[str] = None
        self.output_filename: Optional[str] = None
        self.error_message: Optional[str] = None
        self.error_code: Optional[str] = None
        self.error_details: Optional[dict] = None
        self.translation_repair_message: Optional[str] = None
        self.step_durations: dict = {}
        self.total_duration: Optional[float] = None
        self.validation: Optional[dict] = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

    def to_status_dict(self) -> dict:
        # 构建每步状态数组（前端轮询展示用）
        steps = []
        for s in PIPELINE_STEPS:
            step_key = s["key"]
            if step_key == "matching":
                step_status = "skipped"  # 步骤5待后续开发
            elif self.status == "pending":
                step_status = "pending"
            elif self.status == "completed":
                step_status = "completed"
            elif self.status == "failed":
                step_status = "failed" if s["index"] == self.step_index else "completed" if s["index"] < self.step_index else "pending"
            else:  # processing
                if s["index"] < self.step_index:
                    step_status = "completed"
                elif s["index"] == self.step_index:
                    step_status = "in_progress"
                else:
                    step_status = "pending"
            
            steps.append({
                "step": s["index"],
                "name": s["name"],
                "key": step_key,
                "status": step_status,
                "duration": f"{self.step_durations[step_key]}s" if step_key in self.step_durations else None,
            })

        status_dict = {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "steps": steps,
            "required_input": self.gender_confirmation.required_input,
            "message": self._get_message(),
            "error_message": self.error_message,
            "error_code": self.error_code,
            "error_details": self.error_details,
            "step_durations": self.step_durations,
            "total_duration": self.total_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

        # 任务完成时携带结果数据（供前端预览&下载）
        if self.status == "completed":
            status_dict["result"] = self.to_result_dict()

        return status_dict

    def to_result_dict(self) -> dict:
        # 构建 PPTX/PDF 双格式下载 URL
        pptx_download_url = None
        pdf_download_url = None
        pdf_available = False
        
        if self.output_filename:
            encoded = urllib.parse.quote(self.output_filename, safe='')
            pptx_download_url = f"/api/v1/records/{self.task_id}/download?format=pptx"
            
            # 检查 PDF 是否存在
            pdf_filename = self.output_filename
            if pdf_filename.endswith('.pptx'):
                pdf_filename = pdf_filename[:-5] + '.pdf'
            elif not pdf_filename.endswith('.pdf'):
                pdf_filename += '.pdf'
            
            # PDF 输出目录与 PPTX 相同
            from app.services.smart_filler_service import SmartFillerService
            pdf_path = self.pdf_path or (os.path.splitext(self.output_path)[0] + ".pdf" if self.output_path else os.path.join(SmartFillerService.OUTPUT_DIR, pdf_filename))
            pdf_available = os.path.exists(pdf_path)
            
            if pdf_available:
                pdf_download_url = f"/api/v1/records/{self.task_id}/download?format=pdf"

        # 从 resume_data 提取扁平化预览字段
        rd = self.resume_data or {}
        # work 数组第一项的公司名作为 current_company
        work_list = rd.get("work", [])
        current_company = work_list[0].get("company", "") if work_list else ""
        # skills 合并 tech_skills + lang_skills
        skills = []
        if rd.get("tech_skills"):
            skills.append(str(rd["tech_skills"]))
        if rd.get("lang_skills"):
            skills.append(str(rd["lang_skills"]))

        result = {
            "task_id": self.task_id,
            "status": self.status,
            "success": self.status == "completed",
            "output_filename": self.output_filename,
            "download_url": pptx_download_url,  # 向后兼容, 默认指向 PPTX
            "pptx_download_url": pptx_download_url,
            "pdf_download_url": pdf_download_url,
            "pdf_available": pdf_available,
            "resume_data": self.resume_data,
            "validation": self.validation,
            "step_durations": self.step_durations,
            "total_duration": self.total_duration,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "error_details": self.error_details,
            "message": self._get_message(),
            # 扁平化预览字段（前端 previewData 直接使用）
            "name": rd.get("name", ""),
            "anonymized_name": rd.get("name", ""),  # 脱敏后的姓名（当前与 name 一致）
            "position": rd.get("position", ""),
            "total_exp": rd.get("total_exp", ""),
            "current_company": current_company,
            "match_rate": None,
            "match_level": None,
            "skills": skills,
        }
        return result

    def _get_message(self) -> str:
        if self.status == "pending":
            return "任务已创建，等待处理"
        elif self.status == "processing":
            if self.translation_repair_message:
                return self.translation_repair_message
            return f"正在执行: {self.current_step}"
        elif self.status == "completed":
            return "处理完成 ✅"
        elif self.status == "failed":
            return f"处理失败: {self.error_message}"
        return ""


class PipelineService:
    @staticmethod
    def detect_target_position_language(
        job_position: str,
    ) -> Optional[str]:
        """Detect CN/EN for a clearly Chinese or English position."""
        text = (job_position or "").strip()
        if not text:
            return None
        if re.search(r"[\u3400-\u9fff]", text):
            return "CN"
        if re.search(r"[A-Za-z]", text):
            return "EN"
        return None

    @classmethod
    def validate_target_position_language(
        cls, job_position: str, output_language: str
    ) -> Optional[str]:
        """Return an error message when position and output languages differ."""
        position_language = cls.detect_target_position_language(job_position)
        normalized_output = (output_language or "").strip().upper()
        if position_language and position_language != normalized_output:
            return (
                "目标岗位语言必须与输出语言一致；"
                "请调整目标岗位或输出语言后再处理。"
            )
        return None

    """
    Pipeline 编排服务

    负责按顺序执行6个处理步骤，实时更新任务进度。
    使用内存字典存储任务状态，支持异步轮询。
    """

    # 内存任务存储 (task_id -> TaskInfo)
    _tasks: Dict[str, TaskInfo] = {}
    _lock = threading.Lock()

    @classmethod
    def create_task(cls, file_id: str, template_type: str = "vertical",
                    target_language: str = "EN", job_position: str = "",
                    template_language: str = "", department: str = "") -> str:
        """创建新任务并返回 task_id"""
        task_id = str(uuid.uuid4())
        task = TaskInfo(
            task_id=task_id,
            file_id=file_id,
            template_type=template_type,
            target_language=target_language,
            job_position=job_position,
            template_language=template_language,
            department=department,
        )
        with cls._lock:
            cls._tasks[task_id] = task
        return task_id

    @classmethod
    def get_task(cls, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        with cls._lock:
            return cls._tasks.get(task_id)

    @classmethod
    def get_all_tasks(cls) -> list:
        """获取所有任务列表（按创建时间倒序）"""
        with cls._lock:
            tasks = list(cls._tasks.values())
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks

    @classmethod
    def _update_progress(cls, task: TaskInfo, step: dict, progress: int):
        """更新任务进度"""
        task.current_step = step["name"]
        task.step_index = step["index"]
        task.progress = progress
        task.updated_at = datetime.utcnow()
        from app.services.access_service import persist_task
        persist_task(task, "cv")

    @staticmethod
    async def _resolve_target_technical_area(
        job_position: str, output_language: str
    ) -> str:
        """Use only the user-supplied target position for the template field."""
        requested_position = (job_position or "").strip()
        if not requested_position:
            return ""

        target_language = (output_language or "").upper()
        if target_language not in ("CN", "EN"):
            return requested_position

        if re.search(r"[\u3400-\u9fff]", requested_position):
            source_language = "CN"
        elif re.search(r"[A-Za-z]", requested_position):
            source_language = "EN"
        else:
            return requested_position

        if source_language == target_language:
            return requested_position

        return await TranslatorService.translate_text(
            requested_position,
            source_language,
            target_language,
            context="技术领域",
            field_path="technical_area",
        )

    @classmethod
    async def run_pipeline(cls, task_id: str):
        """
        执行完整的 Pipeline 流程（异步）

        步骤顺序:
          1. 文档解析
          2. LLM结构化抽取
          3. 翻译+脱敏
          4. 约束性摘要
          6. PPT模板填充
        """
        task = cls.get_task(task_id)
        if not task:
            return

        task.status = "processing"
        task.updated_at = datetime.utcnow()
        total_start = time.time()
        total_steps = len(ACTIVE_STEPS)
        step_counter = 0

        def report_repair(path, attempt, reason):
            task.translation_repair_message = (
                f"正在复核并修复翻译（第 {attempt}/{TranslatorService.MAX_TRANSLATION_ATTEMPTS - 1} 轮），达到上限后保留结果并继续生成"
            )
            task.updated_at = datetime.utcnow()

        repair_token = translation_repair_observer.set(report_repair)
        try:
            # ── 步骤1: 文档解析 ──
            step = PIPELINE_STEPS[0]
            step_counter += 1
            cls._update_progress(task, step, int(step_counter / total_steps * 100))

            file_path = cls._find_uploaded_file(task.file_id)
            if not file_path:
                raise FileNotFoundError(f"文件不存在: {task.file_id}")

            t0 = time.time()
            if task.raw_text is None:
                parse_result = await ParserService.parse_file(file_path, task.file_id)
                task.raw_text = parse_result.get("text_content", "")
            task.step_durations.setdefault("parsing", round(time.time() - t0, 2))

            # ── 步骤2: LLM结构化抽取 ──
            step = PIPELINE_STEPS[1]
            step_counter += 1
            cls._update_progress(task, step, int(step_counter / total_steps * 100))

            t0 = time.time()
            cached = task.gender_confirmation.extracted
            resume_data: ResumeData = ResumeData(**cached) if cached is not None else await ExtractorService.extract_structure(task.raw_text)
            # Structural preparation for constrained summarization: when a
            # resume nests dated projects under work history, preserve them as
            # projects before anonymization/translation.
            resume_data = SummarizationService.recover_work_history(
                resume_data, task.raw_text
            )
            resume_data = SummarizationService.recover_embedded_projects(
                resume_data, task.raw_text
            )
            task.step_durations.setdefault("extracting", round(time.time() - t0, 2))
            gender = task.gender_confirmation.inspect(task.raw_text, resume_data)
            if gender is None:
                task.status = "awaiting_input"
                task.updated_at = datetime.utcnow()
                return
            resume_data.gender = gender

            # ── 步骤3: 翻译+脱敏 ──
            step = PIPELINE_STEPS[2]
            step_counter += 1
            cls._update_progress(task, step, int(step_counter / total_steps * 100))

            t0 = time.time()

            # 3a. 脱敏 (同步)
            final_lang = task.template_language or task.target_language
            if final_lang:
                final_lang = final_lang.upper()

            anonymized = AnonymizerService.anonymize_resume(resume_data)

            # 3b. 翻译 (异步) - 如果需要
            if final_lang and final_lang in ("CN", "EN"):
                # The extractor language is advisory; honor the explicit target.
                translated = await TranslatorService.translate_resume(anonymized, final_lang)
            else:
                translated = anonymized

            resume_data = translated
            task.translation_repair_message = None
            task.step_durations["transforming"] = round(time.time() - t0, 2)

            # ── 步骤4: 约束性摘要 ──
            step = PIPELINE_STEPS[3]
            step_counter += 1
            cls._update_progress(task, step, int(step_counter / total_steps * 100))

            t0 = time.time()
            summarized = await SummarizationService.summarize_resume(resume_data)
            resume_data = summarized
            resume_data = SummarizationService.sanitize_experience_data(resume_data)
            resume_data.total_exp = TranslatorService.normalize_total_experience(
                resume_data, final_lang
            )

            requested_position = (task.job_position or "").strip()
            resume_data.technical_area = await cls._resolve_target_technical_area(
                requested_position, final_lang
            )

            # Write all derived position fields before the final language audit.
            if requested_position:
                if re.search(r"[\u3400-\u9fff]", requested_position):
                    position_source_language = "CN"
                elif re.search(r"[A-Za-z]", requested_position):
                    position_source_language = "EN"
                else:
                    position_source_language = final_lang

                resume_data.job_position = await TranslatorService.translate_text(
                    requested_position,
                    position_source_language,
                    final_lang,
                    context="目标岗位",
                    field_path="job_position",
                )
                if position_source_language == "EN":
                    resume_data.job_position_en = requested_position
                else:
                    resume_data.job_position_en = await TranslatorService.translate_text(
                        requested_position,
                        position_source_language,
                        "EN",
                        context="目标岗位英文名称",
                        field_path="job_position_en",
                    )

            if final_lang in ("CN", "EN"):
                resume_data = await TranslatorService.review_and_retranslate(
                    resume_data, final_lang
                )
            task.step_durations["summarizing"] = round(time.time() - t0, 2)
            task.translation_repair_message = None

            # ── 步骤5: 岗位匹配评估 [跳过] ──
            # 留待后续开发

            # ── 步骤6: PPT模板填充 ──
            step = PIPELINE_STEPS[5]  # 索引5是第6步
            step_counter += 1
            cls._update_progress(task, step, int(step_counter / total_steps * 100))

            t0 = time.time()

            # 调用智能填充服务 (同步) — 文件名自动生成
            # Revalidate degrees after LLM stages so preview and exports agree.
            from app.schemas.education import normalize_degree
            for education in resume_data.education:
                education.degree = normalize_degree(education.degree)

            result = await asyncio.to_thread(
                SmartFillerService.fill_template,
                resume_data,
                orientation=task.template_type,
                generate_pdf=True,
            )

            task.output_path = result["pptx_path"]
            task.pdf_path = result.get("pdf_path")
            task.output_filename = result["filename"]
            task.step_durations["filling"] = round(time.time() - t0, 2)

            # ── PPT验证 ──
            try:
                validation_result = validate_pptx(result["pptx_path"])
                task.validation = validation_result.to_dict()
            except Exception:
                task.validation = None
            else:
                package_errors = [
                    issue
                    for issue in validation_result.errors
                    if issue.category == "package_integrity"
                ]
                if package_errors:
                    raise ValueError(
                        "生成的 PPTX 包结构无效，已阻止归档: "
                        + "; ".join(issue.description for issue in package_errors)
                    )

            # ── 保存最终 resume_data ──
            task.resume_data = resume_data.model_dump() if resume_data else None

            # ── 完成 ──
            task.status = "completed"
            task.progress = 100
            task.total_duration = round(time.time() - total_start, 2)
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()

        except TranslationQualityError as e:
            task.status = "failed"
            task.error_message = str(e)
            task.error_code = e.error_code
            task.error_details = e.to_detail()
            task.total_duration = round(time.time() - total_start, 2)
            task.updated_at = datetime.utcnow()
            logger.warning(
                "Translation quality check failed; target=%s fields=%s",
                e.target_language,
                e.field_paths,
            )
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.error_code = None
            task.error_details = None
            task.total_duration = round(time.time() - total_start, 2)
            task.updated_at = datetime.utcnow()

        finally:
            translation_repair_observer.reset(repair_token)
            from app.services.access_service import persist_task
            persist_task(task, "cv")

    @classmethod
    def _find_uploaded_file(cls, file_id: str) -> Optional[str]:
        """在 uploads 目录中查找已上传的文件"""
        if not os.path.exists(UPLOAD_DIR):
            return None
        for f in os.listdir(UPLOAD_DIR):
            if f.startswith(file_id):
                return os.path.join(UPLOAD_DIR, f)
        return None

    @classmethod
    def start_pipeline(cls, task_id: str):
        """
        在独立线程中启动 Pipeline 执行（非阻塞）

        关键修复：不能在 FastAPI 主事件循环上运行 Pipeline，因为
        Pipeline 内部包含同步 I/O 操作（文档解析、PPT 生成），
        会阻塞事件循环导致所有 API 请求挂起（包括轮询请求）。
        解决方案：启动独立线程，在线程内创建新的 asyncio 事件循环。
        """
        thread = threading.Thread(
            target=cls._run_pipeline_in_thread,
            args=(task_id,),
            daemon=True,
            name=f"pipeline-{task_id[:8]}"
        )
        thread.start()

    @classmethod
    def _run_pipeline_in_thread(cls, task_id: str):
        """在独立线程中创建事件循环并执行 Pipeline"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cls.run_pipeline(task_id))
        except Exception as e:
            # 线程内异常记录到任务中
            task = cls.get_task(task_id)
            if task and task.status != "failed":
                task.status = "failed"
                task.error_message = f"Pipeline 线程异常: {str(e)}"
                task.updated_at = datetime.utcnow()
        finally:
            loop.close()
