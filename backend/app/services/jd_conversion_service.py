from __future__ import annotations

import asyncio
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.schemas.jd_conversion import (
    BilingualItems,
    JDContent,
    JDConversionRequest,
    JDOutputLanguage,
    JDPositionRecognitionRequest,
)
from app.services.jd_document_service import JDDocumentService
from app.services.llm_service import LLMService
from app.services.parser_service import ParserService
from app.services.translator_service import TranslatorService


CN_OTHER_DUTY = "负责上级安排的其他工作。"
EN_OTHER_DUTY = "Complete other tasks assigned by the supervisor."


@dataclass
class JDTaskInfo:
    task_id: str
    request: JDConversionRequest
    status: str = "pending"
    progress: int = 0
    current_step: str = ""
    error_message: Optional[str] = None
    raw_text: str = ""
    content: Optional[JDContent] = None
    output_filename: Optional[str] = None
    docx_path: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_available: bool = False
    resolved_target_position: str = ""
    target_position_source: str = "content"
    generation_mode: str = "standardize"
    source_location_found: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    STEPS = (
        ("parsing", "Document parsing"),
        ("standardizing", "JD standardization"),
        ("validating", "Bilingual validation"),
        ("awaiting_location", "Work location confirmation"),
        ("generating", "Word and PDF generation"),
    )

    def status_dict(self) -> dict:
        steps = []
        current_index = next(
            (i for i, (key, _) in enumerate(self.STEPS) if key == self.current_step),
            -1,
        )
        for index, (key, name) in enumerate(self.STEPS):
            if self.status == "completed":
                step_status = "completed"
            elif self.status == "failed" and index == current_index:
                step_status = "failed"
            elif index < current_index:
                step_status = "completed"
            elif index == current_index and self.status in {"processing", "awaiting_input"}:
                step_status = "in_progress"
            else:
                step_status = "pending"
            steps.append({"step": index + 1, "key": key, "name": name, "status": step_status})

        result = None
        if self.status == "completed" and self.content:
            result = {
                "task_id": self.task_id,
                "output_filename": self.output_filename,
                "docx_download_url": f"/api/v1/jd-conversion/tasks/{self.task_id}/download?format=docx",
                "pdf_download_url": (
                    f"/api/v1/jd-conversion/tasks/{self.task_id}/download?format=pdf"
                    if self.pdf_available
                    else None
                ),
                "pdf_available": self.pdf_available,
                "jd_data": self.content.model_dump(),
                "target_position": self.resolved_target_position,
                "target_position_source": self.target_position_source,
                "generation_mode": self.generation_mode,
            }
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "steps": steps,
            "error_message": self.error_message,
            "required_input": (
                {"field": "location", "reason": "missing_source_location"}
                if self.status == "awaiting_input"
                else None
            ),
            "result": result,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class JDConversionService:
    _tasks: dict[str, JDTaskInfo] = {}
    _lock = threading.Lock()

    SYSTEM_PROMPT = """You standardize or create job descriptions for a corporate recruiting team.
Return JSON only. Follow the supplied generation mode exactly.
For a full JD, preserve every factual constraint while improving wording, removing duplication,
correcting the title, and aligning the whole JD with the target position.
For a partial JD, preserve all supplied facts and complete the missing sections conservatively.
For title-only input, create a practical market-standard JD for the target position and category.
When the source does not state a precise experience duration, certification, language level, or
mandatory tool, do not invent a precise hard constraint. Use broadly applicable wording instead.
Never invent a work location. Set source_location_found to true only when a work location is
explicitly present in the source material. If it is absent, return false and leave both location
fields empty. For a detected location, return only the city or region name. Omit country names
and work-arrangement labels such as onsite, remote, or hybrid.
Produce paired Chinese and English content from one semantic structure. A created JD should have
clear responsibilities and useful content in all six requirement groups.
Classify requirements in this exact order: education, experience, required_skills, language,
preferred, soft_skills. Each object has cn and en arrays. Corresponding arrays must have the
same item order and meaning. Do not include markdown, headings, bullets, or the catch-all duty.
"""

    @classmethod
    def create_task(cls, request: JDConversionRequest) -> JDTaskInfo:
        task = JDTaskInfo(task_id=str(uuid.uuid4()), request=request)
        with cls._lock:
            cls._tasks[task.task_id] = task
        return task

    @classmethod
    def get_task(cls, task_id: str) -> Optional[JDTaskInfo]:
        with cls._lock:
            return cls._tasks.get(task_id)

    @classmethod
    def start_task(cls, task_id: str) -> None:
        thread = threading.Thread(
            target=cls._run_in_thread,
            args=(task_id,),
            daemon=True,
            name=f"jd-conversion-{task_id[:8]}",
        )
        thread.start()

    @classmethod
    def _run_in_thread(cls, task_id: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cls.run_task(task_id))
        finally:
            loop.close()
            from app.services.access_service import persist_task
            task = cls.get_task(task_id)
            if task:
                persist_task(task, "jd")

    @classmethod
    async def run_task(cls, task_id: str) -> None:
        task = cls.get_task(task_id)
        if not task:
            return
        task.status = "processing"
        try:
            cls._progress(task, "parsing", 15)
            task.raw_text = await cls._load_source(task.request)
            task.target_position_source = task.request.target_position_source
            task.generation_mode = cls._detect_generation_mode(task.raw_text, task.request)

            cls._progress(task, "standardizing", 50)
            content, task.source_location_found = await cls._standardize_with_analysis(
                task.raw_text,
                task.request,
            )

            cls._progress(task, "validating", 75)
            content = await cls.normalize_content(content)
            if not task.source_location_found:
                content.location_cn = ""
                content.location_en = ""
            else:
                await cls._normalize_location_pair(content)
            task.content = content
            task.resolved_target_position = cls._display_target_position(content, task.request)

            if not (content.location_cn or content.location_en):
                task.status = "awaiting_input"
                cls._progress(task, "awaiting_location", 75)
                return

            await cls._generate_output(task)
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.utcnow()

    @staticmethod
    def _progress(task: JDTaskInfo, step: str, progress: int) -> None:
        task.current_step = step
        task.progress = progress
        task.updated_at = datetime.utcnow()
        from app.services.access_service import persist_task
        persist_task(task, "jd")

    @staticmethod
    async def _load_source(request: JDConversionRequest | JDPositionRecognitionRequest) -> str:
        if request.source_text and request.source_text.strip():
            return request.source_text.strip()
        if not request.file_id:
            return ""
        upload_dir = settings.upload_path
        file_path = next(
            (path for path in upload_dir.iterdir() if path.name.startswith(request.file_id or "")),
            None,
        )
        if file_path is None:
            raise FileNotFoundError(f"Uploaded JD file not found: {request.file_id}")
        parsed = await ParserService.parse_file(str(file_path), request.original_filename or file_path.name)
        return parsed["text_content"]

    @staticmethod
    def _requested_target_position(request: JDConversionRequest) -> str:
        return (request.target_position or request.target_direction or "").strip()

    @classmethod
    def _filename_target_position(cls, original_filename: str) -> str:
        stem = Path(original_filename or "").stem
        if not stem:
            return ""
        value = re.sub(r"(?i)(?:^|[_\s-])20\d{6}(?:[_\s-]\d{6})?$", "", stem)
        value = re.sub(r"(?i)(?:^|[_\s-])(CN\+EN|CNEN|CN|EN)(?=$|[_\s-])", " ", value)
        value = re.sub(r"(?i)^JD(?:[_\s-]+IAV(?:[_\s-]+CN)?)?[_\s-]*", "", value)
        value = re.sub(r"[_]+", " ", value)
        return " ".join(value.split()).strip(" -_")

    @classmethod
    def _target_evidence(cls, request: JDConversionRequest) -> str:
        requested = cls._requested_target_position(request)
        if requested:
            return requested
        if request.target_position_source == "filename":
            return cls._filename_target_position(request.original_filename)
        return ""

    @classmethod
    def _detect_generation_mode(cls, source_text: str, request: JDConversionRequest) -> str:
        text = " ".join((source_text or "").split())
        target = cls._requested_target_position(request)
        if not text or text.casefold() == target.casefold():
            return "title_only"
        heading_hits = len(re.findall(
            r"岗位职责|任职要求|工作职责|职位要求|responsibilit|requirements|your tasks|your skills",
            text,
            re.I,
        ))
        if len(text) >= 350 or heading_hits >= 2:
            return "full_jd"
        if len(text) <= 100 and len(text.split()) <= 12 and not re.search(r"[.;。；:：,，]", text):
            return "title_only"
        return "partial_jd"

    @classmethod
    def _display_target_position(cls, content: JDContent, request: JDConversionRequest) -> str:
        requested = cls._requested_target_position(request)
        if requested:
            return requested
        if request.output_language == "CN":
            return content.title_cn or content.title_en
        return content.title_en or content.title_cn

    @classmethod
    def _apply_requested_target_position(cls, raw: dict, target: str) -> None:
        parts = [part.strip() for part in re.split(r"\s+/\s+", target, maxsplit=1) if part.strip()]
        if len(parts) == 2:
            first_is_cn = bool(re.search(r"[\u3400-\u9fff]", parts[0]))
            second_is_cn = bool(re.search(r"[\u3400-\u9fff]", parts[1]))
            if first_is_cn != second_is_cn:
                raw["title_cn"] = parts[0] if first_is_cn else parts[1]
                raw["title_en"] = parts[1] if first_is_cn else parts[0]
                return
        if re.search(r"[\u3400-\u9fff]", target):
            raw["title_cn"] = target
        else:
            raw["title_en"] = target

    @classmethod
    async def recognize_target_position(cls, request: JDPositionRecognitionRequest) -> str:
        if request.target_position_source == "filename":
            target = cls._filename_target_position(request.original_filename)
            if not target:
                raise ValueError("The filename does not contain a recognizable job title")
            return target

        source_text = await cls._load_source(request)
        if not source_text.strip():
            raise ValueError("The JD source does not contain recognizable content")

        raw = await LLMService.call_llm_json(
            prompt=f"""Extract only the job title from the following job description.
Return this JSON object exactly:
{{"title_cn": "", "title_en": ""}}

Job description:
{source_text}""",
            system_prompt=(
                "You extract job titles for a recruiting system. Return JSON only. "
                "Use the most specific title explicitly supported by the source. "
                "Return concise paired Chinese and English titles without department names, locations, or seniority not present in the source."
            ),
            temperature=0.1,
            max_tokens=300,
        )
        title_cn = cls._clean(str(raw.get("title_cn") or ""))
        title_en = cls._clean(str(raw.get("title_en") or ""))
        if not title_cn and not title_en:
            raise ValueError("The JD content does not contain a recognizable job title")
        if request.output_language == "CN":
            return title_cn or title_en
        if request.output_language == "EN":
            return title_en or title_cn
        return " / ".join(value for value in (title_cn, title_en) if value)

    @classmethod
    async def _standardize(cls, source_text: str, request: JDConversionRequest) -> JDContent:
        content, _ = await cls._standardize_with_analysis(source_text, request)
        return content

    @classmethod
    async def _standardize_with_analysis(
        cls,
        source_text: str,
        request: JDConversionRequest,
    ) -> tuple[JDContent, bool]:
        generation_mode = cls._detect_generation_mode(source_text, request)
        target_evidence = cls._target_evidence(request)
        prompt = f"""Generation mode: {generation_mode}
Preferred target-position source: {request.target_position_source}
Target-position evidence: {target_evidence or '(infer from source content)'}
Original filename: {request.original_filename or '(not supplied)'}

Source material:
{source_text or '(no source body supplied; create from the target position)'}

Department supplied by user: {request.department or '(not supplied)'}
Job category: {request.category}
Target position supplied by user: {cls._requested_target_position(request) or '(not supplied)'}

If a target position is supplied, treat it as authoritative regardless of how it was initially
recognized and use the source material only for supporting details. Otherwise, normalize the title
from the filename evidence or infer it from the source content. Apply the resolved title to the entire JD.

Return this object shape exactly:
{{
  "source_location_found": false,
  "title_cn": "", "title_en": "", "location_cn": "", "location_en": "",
  "department": "", "category": "{request.category}",
  "responsibilities_cn": [], "responsibilities_en": [],
  "requirements": {{
    "education": {{"cn": [], "en": []}},
    "experience": {{"cn": [], "en": []}},
    "required_skills": {{"cn": [], "en": []}},
    "language": {{"cn": [], "en": []}},
    "preferred": {{"cn": [], "en": []}},
    "soft_skills": {{"cn": [], "en": []}}
  }}
}}"""
        raw = await LLMService.call_llm_json(
            prompt=prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=8000,
        )
        requested_target = cls._requested_target_position(request)
        if requested_target:
            cls._apply_requested_target_position(raw, requested_target)
        location_flag = raw.pop("source_location_found", None)
        if isinstance(location_flag, str):
            source_location_found = location_flag.strip().lower() == "true"
        elif location_flag is None:
            source_location_found = bool(
                generation_mode != "title_only"
                and source_text.strip()
                and (raw.get("location_cn") or raw.get("location_en"))
            )
        else:
            source_location_found = location_flag is True
        if not source_location_found:
            raw["location_cn"] = ""
            raw["location_en"] = ""
        raw["department"] = request.department.strip()
        raw["category"] = request.category
        return JDContent.model_validate(raw), source_location_found

    @classmethod
    async def normalize_content(cls, content: JDContent) -> JDContent:
        content.title_cn = cls._clean(content.title_cn)
        content.title_en = cls._clean(content.title_en)
        content.location_cn = cls._clean(content.location_cn)
        content.location_en = cls._clean(content.location_en)
        content.department = cls._clean(content.department)

        if not content.title_cn and content.title_en:
            content.title_cn = await TranslatorService.translate_text(content.title_en, "EN", "CN", "job title")
        if not content.title_en and content.title_cn:
            content.title_en = await TranslatorService.translate_text(content.title_cn, "CN", "EN", "job title")
        if not content.title_cn and not content.title_en:
            raise ValueError("The source JD does not contain a recognizable job title")

        content.responsibilities_cn, content.responsibilities_en = await cls._normalize_pair(
            content.responsibilities_cn,
            content.responsibilities_en,
        )
        content.responsibilities_cn = cls._remove_other_duty(content.responsibilities_cn, "CN")
        content.responsibilities_en = cls._remove_other_duty(content.responsibilities_en, "EN")
        content.responsibilities_cn.append(CN_OTHER_DUTY)
        content.responsibilities_en.append(EN_OTHER_DUTY)

        for key in JDDocumentService.REQUIREMENT_ORDER:
            group: BilingualItems = getattr(content.requirements, key)
            group.cn, group.en = await cls._normalize_pair(group.cn, group.en)
        # Keep API data, preview text, and generated documents consistent.
        # Each Chinese section has its own final full stop: one for the
        # responsibilities block and one for the complete requirements block.
        cls._normalize_section_punctuation([content.responsibilities_cn], "；", "。")
        cls._normalize_section_punctuation([content.responsibilities_en], ".", ".")
        cn_requirement_sections = []
        en_requirement_sections = []
        for key in JDDocumentService.REQUIREMENT_ORDER:
            group = getattr(content.requirements, key)
            cn_requirement_sections.append(group.cn)
            en_requirement_sections.append(group.en)
        cls._normalize_section_punctuation(cn_requirement_sections, "；", "。")
        cls._normalize_section_punctuation(en_requirement_sections, ".", ".")
        return content

    @classmethod
    async def _normalize_location_pair(cls, content: JDContent) -> None:
        content.location_cn = JDDocumentService.region_only_location(content.location_cn)
        content.location_en = JDDocumentService.region_only_location(content.location_en)
        if content.location_cn and not content.location_en:
            content.location_en = await TranslatorService.translate_text(
                content.location_cn, "CN", "EN", "work location"
            )
        elif content.location_en and not content.location_cn:
            content.location_cn = await TranslatorService.translate_text(
                content.location_en, "EN", "CN", "work location"
            )
        elif content.location_en and re.search(r"[\u3400-\u9fff]", content.location_en):
            content.location_en = await TranslatorService.translate_text(
                content.location_en, "CN", "EN", "work location"
            )
        content.location_cn = JDDocumentService.region_only_location(content.location_cn)
        content.location_en = JDDocumentService.region_only_location(content.location_en)

    @classmethod
    async def _set_manual_location(cls, content: JDContent, location: str) -> None:
        value = cls._clean(location)
        parts = [
            JDDocumentService.region_only_location(part)
            for part in re.split(r"\s*(?:/|\||\uff5c)\s*", value)
            if part.strip()
        ]
        parts = [part for part in parts if part]
        cn_part = next((part for part in parts if re.search(r"[\u3400-\u9fff]", part)), "")
        en_part = next((part for part in parts if re.search(r"[A-Za-z]", part)), "")
        if cn_part and en_part:
            content.location_cn = cn_part
            content.location_en = en_part
        elif re.search(r"[\u3400-\u9fff]", value):
            content.location_cn = value
            content.location_en = ""
        else:
            content.location_en = value
            content.location_cn = ""
        await cls._normalize_location_pair(content)
        if not (content.location_cn or content.location_en):
            raise ValueError("Enter a city or region, not only a country or work arrangement")

    @classmethod
    async def _generate_output(cls, task: JDTaskInfo) -> None:
        if not task.content:
            raise ValueError("JD content is not available")
        cls._progress(task, "generating", 90)
        output = await asyncio.to_thread(
            JDDocumentService.generate,
            task.content,
            task.request.output_language,
        )
        cls._apply_output(task, output)
        task.status = "completed"
        task.progress = 100
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        from app.services.access_service import persist_task
        persist_task(task, "jd")

    @classmethod
    async def provide_location(cls, task: JDTaskInfo, location: str) -> JDTaskInfo:
        if task.status != "awaiting_input" or not task.content:
            raise ValueError("This JD task is not waiting for a work location")
        task.status = "processing"
        task.error_message = None
        await cls._set_manual_location(task.content, location)
        task.source_location_found = True
        await cls._generate_output(task)
        return task

    @classmethod
    async def _normalize_pair(cls, cn_items: list[str], en_items: list[str]) -> tuple[list[str], list[str]]:
        cn = [cls._clean(item) for item in cn_items if cls._clean(item)]
        en = [cls._clean(item) for item in en_items if cls._clean(item)]
        total = max(len(cn), len(en))
        for index in range(total):
            if index >= len(cn):
                cn.append(await TranslatorService.translate_text(en[index], "EN", "CN", "JD item"))
            if index >= len(en):
                en.append(await TranslatorService.translate_text(cn[index], "CN", "EN", "JD item"))
            elif re.search(r"[\u3400-\u9fff]", en[index]):
                en[index] = await TranslatorService.translate_text(en[index], "CN", "EN", "JD item")
        return cn, en

    @staticmethod
    def _clean(value: str) -> str:
        value = re.sub(r"^[\s\-•·▪●○]+", "", str(value or ""))
        return " ".join(value.replace("\xa0", " ").split())

    @classmethod
    def _normalize_section_punctuation(
        cls,
        sections: list[list[str]],
        separator: str,
        final: str,
    ) -> None:
        """Apply terminal punctuation across one logical JD section."""
        non_empty: list[tuple[list[str], int]] = []
        terminal_pattern = re.compile(r"[。．.!！？!?,，；;:：]+$")
        for section in sections:
            for index, item in enumerate(section):
                value = terminal_pattern.sub("", str(item or "")).strip()
                section[index] = value
                if value:
                    non_empty.append((section, index))
        last_section, last_index = non_empty[-1] if non_empty else (None, None)
        for section, index in non_empty:
            value = section[index]
            is_last = section is last_section and index == last_index
            section[index] = f"{value}{final if is_last else separator}"

    @staticmethod
    def _remove_other_duty(items: list[str], language: str) -> list[str]:
        if language == "CN":
            return [item for item in items if "上级安排的其他工作" not in item]
        return [
            item
            for item in items
            if not re.search(r"other (tasks|duties).*(assigned|supervisor|manager)", item, re.I)
        ]

    @staticmethod
    def _apply_output(task: JDTaskInfo, output: dict) -> None:
        task.output_filename = output["filename"]
        task.docx_path = output["docx_path"]
        task.pdf_path = output["pdf_path"]
        task.pdf_available = output["pdf_available"]

    @classmethod
    async def regenerate(cls, task: JDTaskInfo, content: JDContent) -> JDTaskInfo:
        task.status = "processing"
        cls._progress(task, "validating", 75)
        task.content = await cls.normalize_content(content)
        if not (task.content.location_cn or task.content.location_en):
            task.status = "awaiting_input"
            cls._progress(task, "awaiting_location", 75)
            return task
        await cls._normalize_location_pair(task.content)
        await cls._generate_output(task)
        return task
