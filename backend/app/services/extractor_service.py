"""
信息抽取服务
使用LLM从原始文本中抽取结构化信息
"""
import logging
import os
import re
from typing import Dict, Any
from fastapi import HTTPException
from app.services.llm_service import LLMService
from app.schemas.resume import ResumeData
from app.core.cv_rules import CV_RULES
from app.prompts import load_cv_extraction_prompt


logger = logging.getLogger(__name__)


class ExtractorService:
    _NAME_STOPWORDS = {
        "简历", "中文", "英文", "岗位", "工程师", "测试", "resume", "cv",
        "curriculum", "vitae", "profile", "english", "chinese", "智能", "驾驶",
        "需求", "管理", "职位", "个人", "工作", "项目",
    }

    # Deterministic recovery for common named software/tools. These entries
    # are also the canonical labels used when the model returns a verbose
    # phrase such as "CANoe software". Keep languages, protocols, methods and
    # hardware out of this catalog.
    _SOFTWARE_TERMS = (
        (r"\bCANoe\b", "CANoe"),
        (r"\bCANalyzer\b", "CANalyzer"),
        (r"\bADB\b", "ADB"),
        (r"\bINCA\b", "INCA"),
        (r"\bMDA\b", "MDA"),
        (r"\bMATLAB\b", "MATLAB"),
        (r"\bSimulink\b", "Simulink"),
        (r"\bMicrosoft\s+Office\b|\bMS\s+Office\b", "Microsoft Office"),
        (r"\bExcel\b", "Excel"),
        (r"\bPowerPoint\b", "PowerPoint"),
        (r"\bVisio\b", "Visio"),
        (r"\bJira\b", "Jira"),
        (r"\bConfluence\b", "Confluence"),
        (r"\bAxure\b", "Axure"),
        (r"\bXmind\b", "XMind"),
        (r"\bGit\b", "Git"),
        (r"\bDocker\b", "Docker"),
        (r"\bKubernetes\b", "Kubernetes"),
    )

    _NON_SOFTWARE_SKILLS = {
        # Programming and query languages
        "c", "c++", "c#", "go", "java", "javascript", "kotlin", "matlab language",
        "python", "r", "rust", "sql", "swift", "typescript", "vba",
        # Frameworks/libraries/runtimes
        "angular", "django", "flask", "node.js", "nodejs", "numpy", "pandas",
        "pytorch", "react", "scikit-learn", "spring", "tensorflow", "vue", "vue.js",
        # Protocols, hardware/domains and methods
        "adas", "agile", "can", "capl", "ecu", "ethernet", "hil", "http", "lin",
        "mqtt", "scrum", "test bench", "uds",
        # Operating systems and cloud providers are outside the strict
        # software/tool scope requested for the CV footer.
        "android", "aws", "azure", "gcp", "linux", "office", "windows",
    }

    @staticmethod
    def _filename_name(original_filename: str) -> str:
        if not original_filename:
            return ""
        stem = os.path.splitext(os.path.basename(original_filename))[0]
        for value in reversed(re.findall(r"[\u4e00-\u9fff]{2,4}", stem)):
            if not any(word in value for word in ExtractorService._NAME_STOPWORDS):
                return value
        tokens = [
            token for token in re.findall(r"[A-Za-z]+", stem)
            if token.lower() not in ExtractorService._NAME_STOPWORDS
        ]
        return " ".join(tokens[:3]) if len(tokens) >= 2 else ""

    @staticmethod
    def _text_name(raw_text: str) -> str:
        for line in (raw_text or "").splitlines()[:30]:
            chinese_candidate = line.strip()
            if (
                re.fullmatch(r"[\u4e00-\u9fff]{2,4}", chinese_candidate)
                and not any(
                    word in chinese_candidate
                    for word in ExtractorService._NAME_STOPWORDS
                )
            ):
                return chinese_candidate
            candidate = re.sub(
                r"^[^A-Za-z]+|[^A-Za-z .'-]+$", "", line.strip()
            )
            if re.fullmatch(
                r"[A-Z][A-Za-z'-]{1,30}(?:\s+[A-Z][A-Za-z'-]{1,30}){1,3}",
                candidate,
            ):
                return candidate
        return ""

    @staticmethod
    def _resolve_name(
        extracted_name: str, raw_text: str, original_filename: str
    ) -> str:
        filename_name = ExtractorService._filename_name(original_filename)
        if filename_name and re.search(r"[\u4e00-\u9fff]", filename_name):
            return filename_name
        normalized = (extracted_name or "").strip()
        invalid_names = {
            "f", "n/a", "na", "candidate", "mr. candidate", "ms. candidate"
        }
        if normalized and normalized.lower() not in invalid_names and len(normalized) > 1:
            return normalized
        return filename_name or ExtractorService._text_name(raw_text) or normalized

    @staticmethod
    def _normalize_period(period: str) -> str:
        if not period:
            return period
        value = str(period).strip()
        value = re.sub(r"[~～—–]+", " - ", value)
        value = re.sub(
            r"\s*(?:至今|现在|now|present|current)\s*",
            " - Present ",
            value,
            flags=re.I,
        )
        dates = re.findall(r"(?<!\d)(\d{4})[./-](\d{1,2})(?!\d)", value)
        if len(dates) >= 2:
            return (
                f"{dates[0][0]}.{int(dates[0][1]):02d} - "
                f"{dates[1][0]}.{int(dates[1][1]):02d}"
            )
        if len(dates) == 1 and "Present" in value:
            return f"{dates[0][0]}.{int(dates[0][1]):02d} - Present"
        return re.sub(r"\s*-\s*", " - ", value)

    @staticmethod
    def _enrich_project_periods(projects: list, raw_text: str) -> None:
        if not raw_text or not projects:
            return
        date_pattern = (
            r"\b\d{4}[./-]\d{1,2}\s*(?:[-~～—–]|至今)\s*"
            r"(?:\d{4}[./-]\d{1,2}|至今|Present|now)?\b"
        )
        for project in projects:
            if not isinstance(project, dict) or project.get("period"):
                continue
            name = str(project.get("name") or "").strip()
            if not name:
                continue
            index = raw_text.lower().find(name.lower())
            if index < 0:
                continue
            matches = re.findall(date_pattern, raw_text[index:index + 700])
            if not matches:
                matches = re.findall(
                    date_pattern, raw_text[max(0, index - 350):index]
                )
            if matches:
                project["period"] = ExtractorService._normalize_period(matches[0])

    @staticmethod
    def _skill_items(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [
            item.strip()
            for item in re.split(r"[;；,，\n]+", str(value or ""))
            if item.strip()
        ]

    @staticmethod
    def _has_source_evidence(candidate: str, raw_text: str) -> bool:
        """Require a model candidate to occur verbatim in the parsed source."""
        normalized_candidate = re.sub(r"\s+", " ", candidate).strip()
        normalized_source = re.sub(r"\s+", " ", raw_text or "")
        if not normalized_candidate or not normalized_source:
            return False
        return normalized_candidate.casefold() in normalized_source.casefold()

    @staticmethod
    def _infer_skills(extracted_data: dict, raw_text: str) -> None:
        """Keep only source-backed named software/tools and recover known ones."""
        found: list[str] = []
        seen: set[str] = set()

        def add(label: str) -> None:
            key = label.casefold()
            if key not in seen:
                seen.add(key)
                found.append(label)

        for candidate in ExtractorService._skill_items(
            extracted_data.get("tech_skills")
        ):
            if candidate.casefold() in ExtractorService._NON_SOFTWARE_SKILLS:
                continue
            canonical = next((
                label
                for pattern, label in ExtractorService._SOFTWARE_TERMS
                if re.search(pattern, candidate, flags=re.IGNORECASE)
                and re.search(pattern, raw_text or "", flags=re.IGNORECASE)
            ), None)
            if canonical:
                add(canonical)
            elif ExtractorService._has_source_evidence(candidate, raw_text):
                add(candidate)

        # The catalog is deterministic recovery, not evidence substitution:
        # every item is still matched against the original parsed text.
        for pattern, label in ExtractorService._SOFTWARE_TERMS:
            if re.search(pattern, raw_text or "", flags=re.IGNORECASE):
                add(label)

        extracted_data["tech_skills"] = "; ".join(found) if found else None

    @staticmethod
    def _task_items(text: str) -> list[str]:
        if not text or not str(text).strip():
            return []
        value = str(text).replace("\\n", "\n").replace("\r\n", "\n").strip()
        lines = [line.strip() for line in value.split("\n") if line.strip()]
        bullet_pattern = (
            r"^[•·▪▸►●○◆◇❖➢✓✔☑▫\-*\u2022\u2023\u25e6"
            r"\u2043\u2219⚫]\s*"
        )
        if any(re.match(bullet_pattern, line) for line in lines):
            items = [
                re.sub(bullet_pattern, "", line).strip() for line in lines
            ]
        else:
            items = [
                part.strip()
                for part in re.split(r"[;；]", value)
                if part.strip()
            ]
        return [item for item in items if item]

    @staticmethod
    def _recover_missing_work_tasks(
        extracted_data: dict, raw_text: str
    ) -> None:
        if not raw_text or not extracted_data.get("work"):
            return
        lines = (
            str(raw_text).replace("\\n", "\n").replace("\r\n", "\n")
        ).splitlines()
        bullet_pattern = re.compile(
            r"^\s*(?:[•·▪▸►●○◆◇❖➢✓✔☑▫\-*⚫]|\d+[.)](?=\s))\s*"
        )
        stop_pattern = re.compile(
            r"(?:项目案例|项目经历|教育经历|教育背景|"
            r"Project experience|Education|Projects?)",
            re.IGNORECASE,
        )
        date_pattern = re.compile(r"(?<!\d)(\d{4})[./-]\s*(\d{1,2})")

        def first_period_key(period: str) -> str:
            match = date_pattern.search(str(period or ""))
            return (
                f"{match.group(1)}.{int(match.group(2)):02d}" if match else ""
            )

        def company_tokens(company: str) -> list[str]:
            return re.findall(
                r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}",
                str(company or ""),
            )

        markers = []
        cursor = 0
        for item in extracted_data.get("work", []):
            if not isinstance(item, dict):
                markers.append(None)
                continue
            period_key = first_period_key(item.get("period", ""))
            tokens = company_tokens(item.get("company", ""))
            candidates = []
            for index in range(cursor, len(lines)):
                if (
                    not period_key
                    or period_key not in lines[index].replace(" ", "")
                ):
                    continue
                score = sum(
                    2
                    for token in tokens
                    if token.lower() in lines[index].lower()
                )
                candidates.append((score, index))
            marker = (
                max(candidates, key=lambda value: (value[0], -value[1]))[1]
                if candidates
                else None
            )
            markers.append(marker)
            if marker is not None:
                cursor = marker + 1

        for position, item in enumerate(extracted_data.get("work", [])):
            marker = markers[position] if position < len(markers) else None
            if marker is None or not isinstance(item, dict):
                continue
            end = len(lines)
            if position + 1 < len(markers) and markers[position + 1] is not None:
                end = markers[position + 1]
            bullets = []
            current = None
            for line in lines[marker + 1:end]:
                if stop_pattern.search(line.strip()):
                    break
                match = bullet_pattern.match(line)
                if match:
                    if current:
                        bullets.append(current.strip())
                    current = line[match.end():].strip()
                elif current and line.strip():
                    current += " " + line.strip()
            if current:
                bullets.append(current.strip())
            bullets = [bullet for bullet in bullets if bullet]
            existing_count = len(
                ExtractorService._task_items(item.get("tasks", ""))
            )
            if bullets and len(bullets) > existing_count:
                item["tasks"] = "; ".join(bullets)

    @staticmethod
    def _clear_work_tasks_without_source_evidence(
        extracted_data: dict, raw_text: str
    ) -> None:
        if not raw_text or not extracted_data.get("work"):
            return
        text = str(raw_text).replace("\\n", "\n").replace("\r\n", "\n")
        work_match = re.search(
            r"(?im)^\s*(?:工作经历|工作经验|work\s+experienc\w*)\s*$",
            text,
        )
        project_match = re.search(
            r"(?im)^\s*(?:项目经历|项目案例|project\s+experience)\s*",
            text,
        )
        if (
            not work_match
            or not project_match
            or project_match.start() <= work_match.end()
        ):
            return
        section = text[work_match.end():project_match.start()]
        has_bullets = re.search(
            r"(?im)^\s*(?:[•·▪▸►●○◆◇❖➢✓✔☑▫\-*⚫]|"
            r"\d+[.)](?=\s))\s+\S+",
            section,
        )
        has_label = re.search(
            r"(?i)(?:工作描述|工作职责|job\s+description|"
            r"responsibilit(?:y|ies))\s*:",
            section,
        )
        if has_bullets or has_label:
            return
        for item in extracted_data.get("work", []):
            if isinstance(item, dict):
                item["tasks"] = ""

    @staticmethod
    def _fallback_extract_structure(
        raw_text: str, original_filename: str = ""
    ) -> dict:
        text = raw_text or ""
        data = {
            "name": ExtractorService._resolve_name(
                "", text, original_filename
            ),
            "phone": "",
            "email": "",
            "total_exp": "",
            "language": (
                "CN"
                if len(re.findall(r"[\u4e00-\u9fff]", text)) >= 8
                else "EN"
            ),
            "education": [],
            "work": [],
            "project": [],
        }
        email_match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text
        )
        if email_match:
            data["email"] = email_match.group(0)
        phone_match = re.search(r"(?:\+?86[- ]?)?1[3-9]\d{9}", text)
        if phone_match:
            data["phone"] = phone_match.group(0)
        years = [
            int(value)
            for value in re.findall(
                r"(?<!\d)(?:19|20)\d{2}(?!\d)", text
            )
        ]
        if years:
            data["total_exp"] = f"{max(0, max(years) - min(years))}年"
        ExtractorService._infer_skills(data, text)
        return data

    @staticmethod
    def _responsibility_block_to_tasks(lines: list[str]) -> str:
        '''Convert one Responsibilities block into semicolon-separated tasks.'''
        tasks = []
        current = ''
        bullet = re.compile(r'^\s*[\u2022\u2023\u25e6\u2043\u2219*-]\s*(.+)$')
        for raw_line in lines:
            line = raw_line.strip()
            if not line or re.fullmatch(r'work\s+experience', line, re.I):
                continue
            match = bullet.match(line)
            if match:
                if current:
                    tasks.append(current)
                current = match.group(1).strip()
            elif current:
                current = f'{current} {line}'
            else:
                current = line
        if current:
            tasks.append(current)
        return ';\n'.join(task for task in tasks if task)

    @staticmethod
    def _recover_ordered_responsibility_blocks(raw_text: str, extracted_data: dict) -> None:
        '''Repair multi-column PDFs whose work headings precede all duty blocks.'''
        work = extracted_data.get('work')
        if not isinstance(work, list) or len(work) < 2:
            return
        if not isinstance(work[0], dict) or work[0].get('tasks'):
            return

        heading = re.compile(r'^\s*Responsibilities\s*[:\uff1a]?\s*$', re.I)
        stop = re.compile(
            r'^\s*(?:Performance|Harvest|Skills?|Self-evaluation|Education|Project\s+experience)\s*[:\uff1a]?\s*$',
            re.I,
        )
        blocks = []
        current = None
        for raw_line in (raw_text or '').replace('\\n', '\n').splitlines():
            line = raw_line.strip()
            if heading.match(line):
                if current:
                    blocks.append(current)
                current = []
                continue
            if current is not None and stop.match(line):
                if current:
                    blocks.append(current)
                current = None
                continue
            if current is not None:
                current.append(raw_line)
        if current:
            blocks.append(current)

        recovered = [
            ExtractorService._responsibility_block_to_tasks(block)
            for block in blocks
        ]
        # Only repair an unambiguous one-to-one mapping. Extra responsibility
        # blocks may belong to projects or another section and must not be
        # assigned to work entries by position.
        if len(recovered) != len(work) or not all(recovered):
            return
        for item, tasks in zip(work, recovered):
            if isinstance(item, dict):
                item['tasks'] = tasks

    @staticmethod
    def _recover_education(raw_text: str, extracted_data: dict) -> list:
        """Recover education omitted by the model from an explicit section."""
        aliases = ("education", "educations", "education_background", "academic_background")
        value = next((extracted_data.get(key) for key in aliases if extracted_data.get(key)), None)
        if isinstance(value, dict):
            value = [value]
        if isinstance(value, list) and value:
            aliases = {
                "period": ("period", "date", "dates", "time", "duration", "时间", "时间段"),
                "school": ("school", "university", "institution", "college", "school_name", "学校", "院校"),
                "degree": ("degree", "qualification", "education_level", "学位", "学历"),
                "major": ("major", "field", "specialization", "discipline", "专业", "方向"),
            }
            result = []
            for item in value:
                if isinstance(item, dict):
                    result.append({field: next((item.get(key) for key in keys if item.get(key)), None)
                                   for field, keys in aliases.items()})
            if result:
                return result

        heading = re.compile(r"^\s*(?:education(?:al)?(?:\s+(?:background|history))?|education\s*/\s*training|academic\s+background|教育经历|教育背景|学历背景)\s*[:：]?\s*$", re.I)
        stop = re.compile(r"^\s*(?:work(?:\s+experience)?|professional\s+experience|project(?:\s+experience)?|skills?|languages?|training|工作经历|工作经验|项目经历|技能|语言|培训经历)\s*[:：]?\s*$", re.I)
        period_re = re.compile(r"((?:19|20)\d{2}\s*[-./]\s*(?:19|20)?\d{2}|(?:19|20)\d{2}\s*[-./]\s*\d{1,2})")
        degree_re = re.compile(r"(?:博士|硕士|本科|专科|学士|研究生|ph\.?d|master(?:'s)?|bachelor(?:'s)?|doctor(?:ate)?)", re.I)
        rows, in_section = [], False
        for raw_line in (raw_text or "").replace("\\n", "\n").splitlines():
            line = re.sub(r"^\s*(?:[-*•●▪]|\d+[.)](?=\s))\s*", "", raw_line).strip()
            if not line:
                continue
            if heading.match(line):
                in_section = True
                continue
            if in_section and stop.match(line):
                break
            if not in_section:
                continue
            match = period_re.search(line)
            period = match.group(1).strip() if match else ""
            remainder = line[match.end():].strip(" \t|｜,，") if match else line
            parts = [part.strip() for part in re.split(r"\s{2,}|\t+|\s*[|｜]\s*", remainder) if part.strip()]
            if len(parts) == 1:
                degree_match = degree_re.search(remainder)
                if degree_match:
                    school = remainder[:degree_match.start()].strip(" -|,，")
                    degree = degree_match.group(0)
                    major = remainder[degree_match.end():].strip(" -|,，")
                else:
                    school, degree, major = parts[0], "", ""
            elif parts:
                school = parts[0]
                degree = next((part for part in parts[1:] if degree_re.search(part)), "")
                major = next((part for part in parts[1:] if part != degree), "")
            else:
                continue
            if school:
                rows.append({"period": period, "school": school, "degree": degree, "major": major})
        return rows
    """信息抽取服务"""
    
    @staticmethod
    async def extract_structure(
        raw_text: str, original_filename: str = ""
    ) -> ResumeData:
        """
        从原始文本中抽取结构化简历信息（Pipeline步骤2）
        
        Args:
            raw_text: 原始文本
            
        Returns:
            结构化的简历数据
        """
        logger.info(
            "Resume extraction started; input_chars=%d filename_provided=%s",
            len(raw_text or ""),
            bool(original_filename),
        )
        try:
            # 设计Prompt让LLM提取简历字段
            system_prompt = load_cv_extraction_prompt()

            # 截断过长文本，避免输出超出token限制
            # 中文约1字=1token，预留8000 token给输出JSON
            max_input_chars = CV_RULES.extraction_max_input_chars
            if len(raw_text) > max_input_chars:
                truncated_text = raw_text[:max_input_chars] + "\n[文本过长，已截断]"
            else:
                truncated_text = raw_text
            
            user_prompt = f"""请从以下简历文本中提取结构化信息：

简历文本：
{truncated_text}

请按以下JSON格式返回：
{{
    "name": "姓名",
    "phone": "电话",
    "email": "邮箱",
    "location": "所在地",
    "age": 年龄数字或null,
    "birth_date": "出生日期",
    "position": "应聘职位",
    "technical_area": "技术领域",
    "total_exp": "总工作经验（如：8年）",
    "education": [
        {{
            "period": "时间段",
            "school": "学校",
            "degree": "学位",
            "major": "专业"
        }}
    ],
    "work": [
        {{
            "company": "公司名称",
            "period": "时间段",
            "role": "职位",
            "tasks": "负责XX系统的架构设计；主导了XX功能开发；完成了XX性能优化"
        }}
    ],
    "project": [
        {{
            "company": "公司名称",
            "period": "时间段",
            "name": "项目名称",
            "role": "角色",
            "tasks": "实现了XX模块；设计了XX方案；解决了XX问题"
        }}
    ],
    "tech_skills": "技术技能列表",
    "lang_skills": "语言技能",
    "lang_skills_level": "语言水平",
    "training_exp": "培训经历",
    "summary": "个人简介",
    "language": "CN"
}}"""
            
            # 调用LLM获取JSON响应
            try:
                extracted_data = await LLMService.call_llm_json(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.3,
                    max_tokens=16000,
                )
            except HTTPException as exc:
                logger.warning(
                    "LLM extraction failed; using local fallback; "
                    "status_code=%s",
                    exc.status_code,
                )
                extracted_data = ExtractorService._fallback_extract_structure(
                    raw_text, original_filename
                )

            extracted_data = dict(extracted_data or {})
            extracted_data["name"] = ExtractorService._resolve_name(
                extracted_data.get("name") or "",
                raw_text,
                original_filename,
            )
            for field in ("education", "work", "project"):
                value = extracted_data.get(field)
                if value is None:
                    extracted_data[field] = []
                elif not isinstance(value, list):
                    extracted_data[field] = [value]

            for field in ("work", "project"):
                for item in extracted_data[field]:
                    if isinstance(item, dict) and isinstance(
                        item.get("tasks"), list
                    ):
                        item["tasks"] = "; ".join(
                            str(task) for task in item["tasks"] if task
                        )

            ExtractorService._enrich_project_periods(
                extracted_data["project"], raw_text
            )
            ExtractorService._infer_skills(extracted_data, raw_text)
            if not extracted_data.get("education"):
                extracted_data["education"] = ExtractorService._recover_education(raw_text, extracted_data)

            # 验证并创建ResumeData对象
            ExtractorService._recover_ordered_responsibility_blocks(raw_text, extracted_data)
            ExtractorService._recover_missing_work_tasks(
                extracted_data, raw_text
            )
            ExtractorService._clear_work_tasks_without_source_evidence(
                extracted_data, raw_text
            )
            resume_data = ResumeData(**extracted_data)
            
            # Never let an empty LLM object become a successful blank resume.
            has_resume_content = any((
                resume_data.name,
                resume_data.position,
                resume_data.technical_area,
                resume_data.total_exp,
                resume_data.summary,
                resume_data.tech_skills,
                resume_data.lang_skills,
                resume_data.work,
                resume_data.project,
                resume_data.education,
            ))
            if not has_resume_content:
                raise HTTPException(
                    status_code=422,
                    detail="无法从简历中识别有效内容，请上传包含可读文字的 PDF/DOCX 文件。"
                )
            logger.info(
                "Resume extraction completed; work=%d project=%d education=%d",
                len(resume_data.work),
                len(resume_data.project),
                len(resume_data.education),
            )
            return resume_data
            
        except HTTPException:
            raise
        except Exception as e:
            error_detail = f"信息抽取失败: {str(e)}"
            logger.exception(
                "Resume extraction failed; error_type=%s",
                type(e).__name__,
            )
            raise HTTPException(status_code=500, detail=error_detail)
