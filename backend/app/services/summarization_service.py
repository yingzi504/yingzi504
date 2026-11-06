"""
约束性摘要服务
对简历经历进行优化和摘要（Pipeline 步骤 4）
"""
import re
import traceback
from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException
from app.services.llm_service import LLMService
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem


class SummarizationService:
    """约束性摘要服务"""

    # ---------- 时间线匹配工具 ----------

    @staticmethod
    def _parse_period_range(period: str):
        """将 period 字符串解析为 (start_year, start_month, end_year, end_month)
        None 表示未指定（如 "Present" 则 end 为 None）
        """
        if not period:
            return None
        period = period.strip().replace(' ', '')
        m = re.match(
            r'(\d{4})[./-](\d{1,2})(?:-|~|～|–|—|to|至)'
            r'(Present|Now|现在|至今|(\d{4})[./-](\d{1,2}))',
            period,
            re.IGNORECASE,
        )
        if m:
            sy, sm = int(m.group(1)), int(m.group(2))
            if m.group(3) and m.group(3).lower() in ('present', 'now', '现在', '至今'):
                return (sy, sm, None, None)
            ey, em = int(m.group(4)), int(m.group(5))
            return (sy, sm, ey, em)
        return None

    @staticmethod
    def _periods_overlap(p1, p2) -> bool:
        """判断两个时间段是否有交集"""
        if not p1 or not p2:
            return True  # 无法解析则保守认为有交集
        s1 = p1[0] * 12 + p1[1]
        e1 = p1[2] * 12 + p1[3] if p1[2] is not None else 999999
        s2 = p2[0] * 12 + p2[1]
        e2 = p2[2] * 12 + p2[3] if p2[2] is not None else 999999
        return s1 <= e2 and s2 <= e1

    @staticmethod
    def _period_overlap_months(p1, p2) -> int:
        """Return overlap length for choosing the owning work item."""
        if not p1 or not p2:
            return 0
        start = max(p1[0] * 12 + p1[1], p2[0] * 12 + p2[1])
        end1 = p1[2] * 12 + p1[3] if p1[2] is not None else 999999
        end2 = p2[2] * 12 + p2[3] if p2[2] is not None else 999999
        return max(0, min(end1, end2) - start + 1)

    _PERIOD_VALUE = (
        r'(?:19|20)\d{2}[./-]\d{1,2}\s*'
        r'(?:-|~|～|–|—|to|至)\s*'
        r'(?:(?:19|20)\d{2}[./-]\d{1,2}|present|now|现在|至今)'
    )
    _DATED_PROJECT_RE = re.compile(
        rf'^\s*(?P<period>{_PERIOD_VALUE})\s*[:：]?\s*(?P<name>.+?)\s*$',
        re.IGNORECASE,
    )
    _NAMED_PROJECT_RE = re.compile(
        rf'^\s*(?P<name>.+?)\s+(?P<period>{_PERIOD_VALUE})\s*$',
        re.IGNORECASE,
    )
    _STOP_SECTION_RE = re.compile(
        r'^(?:教育经历|教育背景|学历背景|职业技能|专业技能|技能|语言技能|'
        r'语言和软件能力|培训经历|个人能力|education(?:\s*/\s*training)?|'
        r'qualification|skills?|languages?|training|'
        r'language\s+and\s+software\s+capabilities)\s*[:：]?$',
        re.IGNORECASE,
    )
    _TASK_LABEL_RE = re.compile(
        r'^(?:职责|工作职责|项目职责|主要职责|responsibilities?|duties)\s*[:：]?$',
        re.IGNORECASE,
    )

    _PROJECT_NAME_LABEL_RE = re.compile(
        r'^(?:project\s+name|\u9879\u76ee\u540d\u79f0|\u9879\u76ee\u540d)\s*[:\uff1a]\s*(?P<name>.+?)\s*$',
        re.IGNORECASE,
    )
    _PROJECT_DETAIL_LABEL_RE = re.compile(
        r'^(?:project\s+(?:introduction|description|responsibilities?)|'
        r'\u9879\u76ee(?:\u4ecb\u7ecd|\u63cf\u8ff0|\u804c\u8d23)|'
        r'\u5de5\u4f5c\u5185\u5bb9)\s*[:\uff1a]?\s*$',
        re.IGNORECASE,
    )
    @staticmethod
    def _is_duration_name(name: str) -> bool:
        value = str(name or '').strip().strip('()（）[] ').strip()
        return bool(re.fullmatch(
            r'(?:\d+(?:\.\d+)?\s*(?:年|个月|月|years?|yrs?|months?|mos?)\s*)+',
            value, re.IGNORECASE,
        ))

    @staticmethod
    def _clean_source_line(value: str) -> str:
        return re.sub(
            r'^\s*(?:[•·▪▸►●○◆◇❖➢✓✔☑▫\-*]|\d{1,3}[.)、])\s*',
            '',
            str(value or ''),
        ).strip()

    @staticmethod
    def _looks_like_employer_heading(value: str) -> bool:
        return bool(re.search(
            r'(?:有限公司|股份公司|集团|公司|\blimited\b|\bltd\.?\b|'
            r'\binc\.?\b|\bcorp\.?\b|\bgmbh\b)$',
            str(value or '').strip(),
            re.IGNORECASE,
        ))

    @classmethod
    def _project_identity(cls, project: ProjectItem) -> tuple[str, str]:
        name = re.sub(r'[^\w\u4e00-\u9fff]', '', str(project.name or '')).lower()
        parsed_period = cls._parse_period_range(project.period)
        period = repr(parsed_period) if parsed_period else re.sub(
            r'[\s./~～–—]+', '-', str(project.period or '').lower()
        ).replace('现在', 'present').replace('至今', 'present')
        return name, period

    @classmethod
    def recover_work_history(cls, resume: ResumeData, raw_text: str) -> ResumeData:
        """Restore employer/date headings from a clearly delimited work section."""
        result = resume.model_copy(deep=True)
        if not raw_text:
            return result
        lines = [cls._clean_source_line(line) for line in raw_text.splitlines()]
        work_idx = next((i for i, line in enumerate(lines)
                         if re.fullmatch(r'(?i)(working experience|work experience|work history|\u5de5\u4f5c\u7ecf\u5386)', line)), -1)
        project_idx = next((i for i, line in enumerate(lines)
                            if re.fullmatch(r'(?i)(project experience|projects|\u9879\u76ee\u7ecf\u5386)', line)), len(lines))
        if work_idx < 0:
            return result
        period_re = re.compile(
            r'^(?P<head>.+?)\s+(?P<period>(?:19|20)\d{2}[./-]\d{1,2}\s*'
            r'(?:-|~|to|\u81f3|\u81f3\u4eca|\u73b0\u5728|present|now)\s*'
            r'(?:(?:19|20)\d{2}[./-]\d{1,2}|present|now|\u81f3\u4eca|\u73b0\u5728))\s*$',
            re.IGNORECASE,
        )
        headings = []
        for i in range(work_idx + 1, project_idx):
            match = period_re.match(lines[i])
            if not match:
                continue
            head = match.group('head').strip(' ,，')
            if not head or re.match(r'(?i)^(project|\u9879\u76ee)', head):
                continue
            parts = [part.strip() for part in re.split(r'[,，]', head) if part.strip()]
            company_parts = parts[:1]
            role_idx = 1
            while role_idx < len(parts) and re.fullmatch(
                r'(?i)(?:co|company|corp|corporation|inc|incorporated|ltd|limited|llc)\.?',
                parts[role_idx],
            ):
                company_parts.append(parts[role_idx])
                role_idx += 1
            company = ', '.join(company_parts) if company_parts else head
            role = parts[role_idx] if role_idx < len(parts) else None
            task_lines = []
            for following in lines[i + 1:project_idx]:
                if period_re.match(following):
                    break
                if following:
                    task_lines.append(following)
            headings.append((company, match.group('period').strip(), role, task_lines))
        if not headings:
            return result

        def normalized_company(company):
            tokens = re.findall(r'[A-Za-z0-9\u4e00-\u9fff]+', str(company or '').lower())
            suffixes = {
                'co', 'company', 'corp', 'corporation', 'inc', 'incorporated',
                'ltd', 'limited', 'llc',
            }
            while tokens and tokens[-1] in suffixes:
                tokens.pop()
            return ''.join(tokens)

        def key(company, period):
            return (normalized_company(company),
                    cls._project_identity(ProjectItem(period=period, name=company))[1])
        existing = {key(item.company, item.period): item for item in result.work}
        ordered = []
        for company, period, role, task_lines in headings:
            item = existing.get(key(company, period))
            if item is None:
                item = WorkItem(company=company, period=period, role=role,
                                tasks='; '.join(task_lines) or None)
            else:
                item.company = company
                item.period = period
                if role:
                    item.role = role
            ordered.append(item)
        matched = {id(item) for item in ordered}
        ordered.extend(item for item in result.work if id(item) not in matched and item.company)
        result.work = ordered
        return result

    @classmethod
    def recover_embedded_projects(cls, resume: ResumeData, raw_text: str) -> ResumeData:
        """Recover projects only inside an explicit project section."""
        result = resume.model_copy(deep=True)
        if not raw_text:
            return result

        lines = [cls._clean_source_line(line) for line in raw_text.splitlines()]
        project_idx = next((i for i, line in enumerate(lines)
                            if re.fullmatch(r'(?i)(project experience|projects|\u9879\u76ee\u7ecf\u5386)', line)), -1)
        scan_start = project_idx + 1 if project_idx >= 0 else 0
        existing = {cls._project_identity(project) for project in result.project}
        recovered: List[ProjectItem] = []

        # Explicit project-name labels are stronger than nearby dated client
        # headings. Charles-style resumes put the actual identity on the
        # Project Name line following the dated client context.
        if project_idx >= 0:
            current_period = None
            found_name_label = False
            for index in range(scan_start, len(lines)):
                line = lines[index]
                dated = cls._DATED_PROJECT_RE.match(line) or cls._NAMED_PROJECT_RE.match(line)
                if dated:
                    current_period = dated.group('period').strip()
                    continue
                named = cls._PROJECT_NAME_LABEL_RE.match(line)
                if not named or cls._is_duration_name(named.group("name")):
                    continue
                found_name_label = True
                tasks = []
                for following in lines[index + 1:]:
                    if cls._PROJECT_NAME_LABEL_RE.match(following):
                        break
                    if cls._DATED_PROJECT_RE.match(following) or cls._NAMED_PROJECT_RE.match(following):
                        break
                    if cls._STOP_SECTION_RE.match(following):
                        break
                    if cls._PROJECT_DETAIL_LABEL_RE.match(following):
                        continue
                    if following:
                        tasks.append(following)
                project_range = cls._parse_period_range(current_period)
                best_work = max(
                    result.work,
                    key=lambda work: cls._period_overlap_months(
                        project_range, cls._parse_period_range(work.period)
                    ),
                    default=None,
                )
                project = ProjectItem(
                    company=best_work.company if best_work else None,
                    period=current_period,
                    name=named.group('name').strip(),
                    role=best_work.role if best_work else None,
                    tasks='; '.join(tasks) or None,
                )
                identity = cls._project_identity(project)
                if identity not in existing:
                    recovered.append(project)
                    existing.add(identity)
            if found_name_label:
                result.project.extend(recovered)
                return result

        for index, line in enumerate(lines[scan_start:], start=scan_start):
            if not line:
                continue
            match = cls._DATED_PROJECT_RE.match(line) or cls._NAMED_PROJECT_RE.match(line)
            if not match:
                continue

            name = match.group('name').strip(' :：|•-')
            period = match.group('period').strip()
            if not name or cls._is_duration_name(name) or cls._looks_like_employer_heading(name):
                continue

            tasks = []
            for following in lines[index + 1:]:
                if not following:
                    continue
                if cls._STOP_SECTION_RE.match(following):
                    break
                if cls._DATED_PROJECT_RE.match(following) or cls._NAMED_PROJECT_RE.match(following):
                    break
                if cls._TASK_LABEL_RE.match(following):
                    continue
                tasks.append(following)

            if not tasks:
                continue

            project_range = cls._parse_period_range(period)
            best_work = None
            best_score = -1
            for work in result.work:
                work_range = cls._parse_period_range(work.period)
                if not cls._periods_overlap(project_range, work_range):
                    continue
                score = cls._period_overlap_months(project_range, work_range)
                if score > best_score:
                    best_work = work
                    best_score = score

            role = best_work.role if best_work else None
            role_key = re.sub(r'\s+', '', str(role or '')).lower()
            tasks = [
                task for task in tasks
                if re.sub(r'\s+', '', task).lower() != role_key
            ]
            if not tasks:
                continue

            project = ProjectItem(
                company=best_work.company if best_work else None,
                period=period,
                name=name,
                role=role,
                tasks='；'.join(tasks),
            )
            identity = cls._project_identity(project)
            if identity not in existing:
                recovered.append(project)
                existing.add(identity)

        result.project.extend(recovered)
        return result

    @staticmethod
    def _auto_fill_project_info(projects: List[ProjectItem], works: List[WorkItem]) -> List[ProjectItem]:
        """根据工作时间线自动补全项目经历中缺失的公司名和职位"""
        if not projects or not works:
            return projects

        result = []
        for proj in projects:
            p = proj.model_copy(deep=True)
            proj_range = SummarizationService._parse_period_range(proj.period)

            # Prefer the work item with the largest overlap.
            best_work = None
            best_score = -1
            for w in works:
                wr = SummarizationService._parse_period_range(w.period)
                if SummarizationService._periods_overlap(proj_range, wr):
                    score = SummarizationService._period_overlap_months(proj_range, wr)
                    if score > best_score:
                        best_work = w
                        best_score = score

            if best_work:
                if not p.company and best_work.company:
                    p.company = best_work.company
                if not p.role and best_work.role:
                    p.role = best_work.role

            result.append(p)

        return result

    @staticmethod
    def _has_text(value) -> bool:
        return value is not None and str(value).strip().lower() not in {'', 'none', 'null'}

    @staticmethod
    def _task_items(text: str) -> List[str]:
        """Split newline, bullet, or semicolon task formats without data loss."""
        if not text or not str(text).strip():
            return []
        items = []
        bullet_pattern = r'^[•·▪▸►●○◆◇❖➢✓✔☑▫\-*\u2022\u2023\u25e6\u2043\u2219]\s*'
        for line in str(text).replace('\r\n', '\n').split('\n'):
            line = re.sub(bullet_pattern, '', line).strip()
            if not line:
                continue
            items.extend(part.strip() for part in re.split(r'[;；]', line) if part.strip())
        return items

    @staticmethod
    def _preserve_task_completeness(original: str, optimized: str) -> str:
        """Do not let project-detail optimization omit source responsibilities."""
        if not original or not original.strip():
            return optimized
        if not optimized or not optimized.strip():
            return original
        original_items = SummarizationService._task_items(original)
        optimized_items = SummarizationService._task_items(optimized)
        if len(optimized_items) < len(original_items):
            return original
        return optimized

    @staticmethod
    def _organize_experience_modules(resume: ResumeData) -> ResumeData:
        """Fill project metadata and keep only meaningful experience modules."""
        source_work = list(resume.work or [])
        projects = list(resume.project or [])
        if projects:
            projects = SummarizationService._auto_fill_project_info(projects, source_work)
        resume.work = [
            work for work in source_work
            if not projects or any(
                SummarizationService._has_text(value)
                for value in (work.company, work.period, work.role, work.tasks)
            )
        ]
        resume.project = projects
        return resume

    @staticmethod
    def _task_similarity(left: str, right: str) -> bool:
        left_norm = re.sub(r'[^\w\u4e00-\u9fff]', '', str(left or '').lower())
        right_norm = re.sub(r'[^\w\u4e00-\u9fff]', '', str(right or '').lower())
        if not left_norm or not right_norm:
            return False
        if left_norm in right_norm or right_norm in left_norm:
            return True
        left_tokens = {left_norm[i:i + 2] for i in range(max(0, len(left_norm) - 1))}
        right_tokens = {right_norm[i:i + 2] for i in range(max(0, len(right_norm) - 1))}
        if not left_tokens or not right_tokens:
            return False
        return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens)) >= 0.7

    @staticmethod
    def _related_projects(work: WorkItem, projects: List[ProjectItem]) -> List[ProjectItem]:
        work_range = SummarizationService._parse_period_range(work.period)
        related = []
        for project in projects:
            project_range = SummarizationService._parse_period_range(project.period)
            if not SummarizationService._periods_overlap(work_range, project_range):
                continue
            if work.company and project.company:
                left = re.sub(r'[^\w\u4e00-\u9fff]', '', work.company.lower())
                right = re.sub(r'[^\w\u4e00-\u9fff]', '', project.company.lower())
                if left and right and left not in right and right not in left:
                    continue
            related.append(project)
        return related

    @staticmethod
    def _deduplicate_work_tasks(
        works: List[WorkItem], projects: List[ProjectItem]
    ) -> List[WorkItem]:
        """Remove project-level details from work overviews."""
        result = []
        for work in works:
            related = SummarizationService._related_projects(work, projects)
            if not related:
                result.append(work)
                continue
            project_items = [
                item for project in related
                for item in SummarizationService._task_items(project.tasks)
            ]
            work_items = SummarizationService._task_items(work.tasks)
            kept = [
                item for item in work_items
                if not any(SummarizationService._task_similarity(item, detail)
                           for detail in project_items)
            ]
            updated = work.model_copy(deep=True)
            updated.tasks = '；'.join(kept)
            result.append(updated)
        return result

    @staticmethod
    def _cleanup_empty_projects(projects: List[ProjectItem]) -> List[ProjectItem]:
        """删除完全无意义的项目条目（连 name 和 tasks 都没有）"""
        return [
            p for p in projects
            if (p.name and p.name.strip()) or (p.tasks and p.tasks.strip())
        ]

    @staticmethod
    def _sanitize_period(period: Optional[str]) -> Optional[str]:
        """Drop clearly invalid calendar months while preserving free-form periods."""
        if period is None:
            return None
        value = str(period).strip()
        if not value:
            return None
        date_tokens = re.findall(r"(?<!\d)(?:19|20)\d{2}[./-](\d{1,2})(?!\d)", value)
        if any(not 1 <= int(month) <= 12 for month in date_tokens):
            return None
        return value

    @staticmethod
    def sanitize_experience_data(resume: ResumeData) -> ResumeData:
        """Remove model hallucinations that cannot represent real experience data."""
        result = resume.model_copy(deep=True)

        def strip_trailing_sections(tasks: Optional[str]) -> Optional[str]:
            items = SummarizationService._task_items(tasks or "")
            kept = []
            for value in items:
                if SummarizationService._STOP_SECTION_RE.fullmatch(value.strip()):
                    break
                kept.append(value)
            if not kept:
                return None
            separator = '；\n' if str(result.language or '').upper() == 'CN' else ';\n'
            return separator.join(kept)

        result.work = [
            item.model_copy(update={
                "period": SummarizationService._sanitize_period(item.period),
                "tasks": strip_trailing_sections(item.tasks),
            })
            for item in result.work
        ]
        result.education = [
            item.model_copy(update={"period": SummarizationService._sanitize_period(item.period)})
            for item in result.education
        ]
        cleaned_projects = []
        for item in result.project:
            name = str(item.name or "").strip()
            if SummarizationService._is_duration_name(name):
                continue
            if name and re.fullmatch(r"[\d\s.,:;|/\\()\[\]{}_-]+", name):
                continue
            cleaned_projects.append(
                item.model_copy(update={
                    "period": SummarizationService._sanitize_period(item.period),
                    "tasks": strip_trailing_sections(item.tasks),
                })
            )
        # Merge only the same named project, period, employer and role. Keep
        # distinct responsibilities; fuzzy matching can discard real differences.
        projects_by_key = {}
        for project in cleaned_projects:
            identity = SummarizationService._project_identity(project)
            key = (*identity, (project.company or '').strip().casefold(),
                   (project.role or '').strip().casefold())
            if not all(identity):
                key = (*key, len(projects_by_key))
            if key not in projects_by_key:
                projects_by_key[key] = project
                continue
            existing = projects_by_key[key]
            tasks = {}
            for task in SummarizationService._task_items(existing.tasks) + SummarizationService._task_items(project.tasks):
                normalized = re.sub(r'\s+', ' ', task).strip(' .;；。').casefold()
                tasks.setdefault(normalized, task)
            existing.tasks = ';\n'.join(tasks.values()) or None
        result.project = list(projects_by_key.values())
        return result

    @staticmethod
    def _cleanup_empty_tail_fields(resume: ResumeData) -> ResumeData:
        """清理尾部空字段 + 统一技能字段标点（分号后空格 + 语言感知标点）"""
        language = resume.language or "CN"
        if resume.lang_skills:
            s = resume.lang_skills.strip()
            if not s:
                resume.lang_skills = None
            else:
                s = re.sub(r';\s*', '; ', s).rstrip()
                resume.lang_skills = SummarizationService._normalize_punctuation(s, language)
        if resume.tech_skills:
            s = resume.tech_skills.strip()
            if not s:
                resume.tech_skills = None
            else:
                skills = {}
                for skill in re.split(r'[;；,，\n]+', s):
                    skill = skill.strip()
                    if skill:
                        skills.setdefault(skill.casefold(), skill)
                s = '; '.join(skills.values())
                resume.tech_skills = SummarizationService._normalize_punctuation(s, language)
        if resume.training_exp and not resume.training_exp.strip():
            resume.training_exp = None
        return resume

    # ---------- 格式化工具 ----------

    @staticmethod
    def _format_multiline_tasks(text: str, language: str = "CN") -> str:
        """
        按分号拆分为多行，每行首字母大写
        模板自带项目符号，因此只需返回纯文本行
        
        根据 language 使用对应语言的分号作为分隔符：
        - CN：中文分号（；）
        - EN：英文分号（;）
        """
        if not text:
            return text
        # 先清理已有的项目符号和多余空白
        text = text.strip()
        # 移除开头的项目符号（连续多个）
        import re
        text = re.sub(r'^[•·▪▸►●○◆◇❖➢✓✔☑▪▫\-*\u2022\u2023\u25E6\u2043\u2219]+', '', text).strip()
        # 按中英文分号拆分
        parts = [p.strip() for p in re.split(r'[;；]', text) if p.strip()]
        if len(parts) <= 1:
            return text
        # 每段首字母大写，其余保持原样
        # 中文无需大写，只对英文有效
        formatted = []
        for p in parts:
            if p:
                # 清理每段中残留的开头项目符号
                p = re.sub(r'^[•·▪▸►●○◆◇❖➢✓✔☑▪▫\-*\u2022\u2023\u25E6\u2043\u2219\s]+', '', p).strip()
                if p:
                    # 每条任务由模板单独显示；去掉模型末尾句号，避免与行间分号叠加。
                    p = re.sub(r"[。．.;；，,]+$", "", p).strip()
                if p:
                    p = p[0].upper() + p[1:]
                    formatted.append(p)
        if not formatted:
            return text
        # 根据语言使用对应分号
        separator = '；\n' if language == "CN" else ';\n'
        return separator.join(formatted)

    # ---------- 标点符号标准化 ----------

    @staticmethod
    def _normalize_punctuation(text: str, language: str = "CN") -> str:
        """根据语言统一标点符号

        - CN: 半角标点 → 全角标点（,.:;!?() → ，。：；！？（））
        - EN: 全角标点 → 半角标点（，。：；！？（） → ,.:;!?()）

        注意：不会替换数字中的小数点或 URL 中的冒号。
        """
        if not text:
            return text

        if language == "CN":
            # 半角 -> 全角
            table = str.maketrans({
                ',': '，',
                ';': '；',
                ':': '：',
                '!': '！',
                '?': '？',
                '(': '（',
                ')': '）',
            })
        else:
            # 全角 -> 半角（句号 . 不替换，避免影响数字和缩写）
            table = str.maketrans({
                '，': ',',
                '；': ';',
                '：': ':',
                '！': '!',
                '？': '?',
                '（': '(',
                '）': ')',
            })

        normalized = text.translate(table)
        # LLM 输出常带句末标点，重新拼接时容易产生“。；”等重复标点。
        normalized = re.sub(r"[。．]\s*[；;]", "；", normalized)
        normalized = re.sub(r"[；;]\s*[。．]", "；", normalized)
        normalized = re.sub(r"[，,]\s*[；;]", "；", normalized)
        normalized = re.sub(r"([。；，！？])\1+", r"\1", normalized)
        return normalized

    @staticmethod
    async def summarize_text(text: str, language: str = "CN") -> str:
        """
        对单个文本进行摘要优化——逐条独立处理，保证数量与内容独特性

        Args:
            text: 原始文本（多条分号分隔的要点）
            language: 语言 ("CN" 或 "EN")

        Returns:
            优化后的文本（同一条数，分号分隔）
        """
        try:
            if not text or not text.strip():
                return text

            import re

            # ── 第一步：按分号拆分成独立要点 ──
            raw_parts = [p.strip() for p in re.split(r'[;；]', text) if p.strip()]
            point_count = len(raw_parts)

            # 如果只有一段，直接用原有方式优化
            if point_count <= 1:
                return await SummarizationService._optimize_single_text(text, language)

            # ── 第二步：每条要点独立优化（并行执行） ──
            tasks = []
            for i, part in enumerate(raw_parts):
                # 清理要点中的残留项目符号
                part = re.sub(r'^[•·▪▸►●○◆◇❖➢✓✔☑▪▫\-*\u2022\u2023\u25E6\u2043\u2219\s]+', '', part).strip()
                if not part:
                    continue
                tasks.append(
                    SummarizationService._optimize_single_bullet(
                        part, i + 1, point_count, language
                    )
                )

            # 并行执行所有 LLM 调用
            import asyncio
            results = await asyncio.gather(*tasks)
            optimized_parts = [r for r in results if r.strip()]

            # ── 第三步：去重（保留顺序，去掉完全重复的要点） ──
            seen = set()
            deduped = []
            for part in optimized_parts:
                # 归一化后比对：去标点、去空格、小写
                key = re.sub(r'[^\w\u4e00-\u9fff]', '', part).lower()
                if key and key not in seen:
                    seen.add(key)
                    deduped.append(part)

            if not deduped:
                return text  # fallback: 返回原文

            # ── 第四步：用分号重新组装 ──
            separator = ';' if language == "EN" else '；'
            result = separator.join(deduped)

            # 语言感知的标点符号统一
            result = SummarizationService._normalize_punctuation(result, language)

            return result

        except Exception as e:
            error_detail = f"文本摘要失败: {str(e)}"
            print(f"[Summarization Error] {error_detail}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_detail)

    @staticmethod
    async def _optimize_single_bullet(
        bullet_text: str, index: int, total: int, language: str
    ) -> str:
        """
        优化单条要点——保持其独特内容

        Args:
            bullet_text: 单条要点的原文
            index: 第几条（从1开始）
            total: 总共几条
            language: 语言

        Returns:
            优化后的单条要点
        """
        lang_desc = "中文" if language == "CN" else "English"
        style_desc = "使用动词开头的句式" if language == "CN" \
            else "use action verb at the beginning"

        length_guide = "控制在1-2行，删除冗余修饰词和重复表述，只保留核心职责和关键成果" if language == "CN" \
            else "keep to 1-2 lines, remove filler words and redundant expressions, retain only core responsibilities and key achievements"

        system_prompt = f"""你是一个专业的简历优化专家。请精准精确简要概括一条{lang_desc}简历职责描述。

核心规则：
1. **精准提炼**：只保留该要点的核心职责和关键量化成果，删除一切冗余修饰词（如"负责了"、"进行了"、"主要是"等废话）
2. **内容忠实**：不得添加原文中没有的新内容，不得虚构数据或成果
3. **独立不合并**：每条要点只描述一个独立的职责或成果，不要与其他要点合并
4. **{style_desc}**
5. **简要控制**：{length_guide}
6. 只返回优化后的文本，不要添加序号、项目符号、前缀或说明"""

        user_prompt = f"""这是第{index}/{total}条要点，请精简优化：

原文：{bullet_text}

直接返回精简后的文本："""

        optimized = await LLMService.call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500
        )

        optimized = optimized.strip()
        # 清理可能被添加的项目符号
        optimized = re.sub(r'^[•·▪▸►●○◆◇❖➢✓✔☑▪▫\-*\u2022\u2023\u25E6\u2043\u2219\s]+', '', optimized).strip()
        # 首字母大写
        if optimized and language == "EN":
            optimized = optimized[0].upper() + optimized[1:]
        elif optimized and language == "CN":
            # 中文去掉可能的前缀数字序号 "1. ", "1、", "(1)" 等
            optimized = re.sub(r'^\d+[.、）\)]\s*', '', optimized).strip()

        return optimized

    @staticmethod
    async def _optimize_single_text(text: str, language: str = "CN") -> str:
        """
        对单段文本进行优化（仅当原文只有一段时使用）
        """
        language_desc = "中文" if language == "CN" else "English"
        resume_style_desc = "常见的简历风格，使用动词开头的句式" if language == "CN" \
            else "standard resume style with action verb at the beginning"

        system_prompt = f"""你是一个专业的简历优化专家。请按照以下规则精准优化简历经历描述：

1. 语法修正：修正语法错误、表达不通顺的地方
2. 句式统一：使用{resume_style_desc}
3. 精准简要：删除冗余修饰词（如"负责了"、"进行了"等），保留核心职责和关键成果
4. 内容忠实：在不大幅改动候选人简历原文内容的基础上进行优化，不虚构内容
5. 禁止添加项目符号：不要添加 •、-、* 等符号，也不要添加数字序号

请直接返回优化后的文本，不要添加其他说明或前缀。"""

        user_prompt = f"""请精简优化以下{language_desc}简历经历描述：

{text}"""

        summarized_text = await LLMService.call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1500
        )

        summarized_text = SummarizationService._normalize_punctuation(
            summarized_text.strip(), language
        )

        return summarized_text
    
    @staticmethod
    async def summarize_work_item(work: WorkItem, language: str = "CN") -> WorkItem:
        """
        优化单个工作经历
        """
        result = work.model_copy(deep=True)
        
        if work.tasks:
            optimized = await SummarizationService.summarize_text(work.tasks, language)
            optimized = SummarizationService._preserve_task_completeness(
                work.tasks, optimized
            )
            result.tasks = SummarizationService._format_multiline_tasks(optimized, language)
        
        return result

    @staticmethod
    async def summarize_work_overview(
        work: WorkItem,
        projects: List[ProjectItem],
        language: str = "CN",
    ) -> WorkItem:
        """Create a short role-level overview while projects keep the detail."""
        result = work.model_copy(deep=True)
        if not projects:
            return await SummarizationService.summarize_work_item(work, language)

        language_name = "Chinese" if language == "CN" else "English"
        project_text = "\n".join(
            f"- {project.period or ''} | {project.name or ''} | {project.tasks or ''}"
            for project in projects
        )
        system_prompt = f"""You restructure resume experience in {language_name}.

Rules:
1. Return 2-4 concise role-level responsibility bullets separated by semicolons.
2. Summarize recurring responsibilities, capabilities, scope, and ownership across projects.
3. Do not include project names, project dates, or step-by-step project details.
4. Do not copy project-detail bullets verbatim; those remain in the Project Experience module.
5. Use only evidence from the source. Do not invent tools, achievements, metrics, or management scope.
6. Return only the semicolon-separated overview, without numbering or bullet symbols."""
        user_prompt = f"""Company: {work.company or ''}
Role: {work.role or ''}
Current work details: {work.tasks or ''}
Projects and detailed responsibilities:
{project_text}"""

        try:
            overview = await LLMService.call_llm(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=800,
            )
        except Exception:
            overview = ""

        items = SummarizationService._task_items(overview)
        project_names = [
            re.sub(r'[^\w\u4e00-\u9fff]', '', project.name or '').lower()
            for project in projects if project.name
        ]
        filtered = []
        for item in items:
            normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', item).lower()
            if any(name and name in normalized for name in project_names):
                continue
            if not any(SummarizationService._task_similarity(item, kept) for kept in filtered):
                filtered.append(item)

        if not filtered:
            non_project = SummarizationService._deduplicate_work_tasks(
                [work], projects
            )[0]
            filtered = SummarizationService._task_items(non_project.tasks)[:3]

        result.tasks = SummarizationService._format_multiline_tasks(
            '；'.join(filtered[:4]), language
        ) if filtered else None
        return result
    
    @staticmethod
    async def summarize_project_item(project: ProjectItem, language: str = "CN") -> ProjectItem:
        """
        优化单个项目经历
        """
        result = project.model_copy(deep=True)
        
        if project.tasks:
            optimized = await SummarizationService.summarize_text(project.tasks, language)
            optimized = SummarizationService._preserve_task_completeness(
                project.tasks, optimized
            )
            result.tasks = SummarizationService._format_multiline_tasks(optimized, language)
        
        return result
    
    @staticmethod
    async def summarize_resume(resume_data: ResumeData) -> ResumeData:
        """
        优化整个简历的所有经历（Pipeline 步骤 4）

        流程:
        1. 优化个人简介
        2. 优化工作经历
        3. 时间线匹配补全项目经历的缺失字段
        4. 优化项目经历
        5. 删除完全无意义的项目条目
        6. 清理尾部空字段
        """
        try:
            language = resume_data.language
            summarized = resume_data.model_copy(deep=True)

            # Apply one structure rule for all resumes: work is an overview,
            # while dated projects retain detailed responsibilities.
            summarized = SummarizationService._organize_experience_modules(summarized)

            # 1. 优化个人简介
            if summarized.summary:
                summarized.summary = await SummarizationService.summarize_text(
                    summarized.summary, language
                )

            # 2. 优化工作经历
            for i, work in enumerate(summarized.work):
                related = SummarizationService._related_projects(
                    work, summarized.project
                )
                if related:
                    summarized.work[i] = await SummarizationService.summarize_work_overview(
                        work, related, language
                    )
                else:
                    summarized.work[i] = await SummarizationService.summarize_work_item(
                        work, language
                    )

            # 3. 时间线匹配：补全项目经历的缺失公司/职位
            summarized.project = SummarizationService._auto_fill_project_info(
                summarized.project, summarized.work
            )

            # 4. 优化项目经历
            for i, project in enumerate(summarized.project):
                summarized.project[i] = await SummarizationService.summarize_project_item(
                    project, language
                )

            # 5. 删除完全无意义的项目条目
            summarized.project = SummarizationService._cleanup_empty_projects(
                summarized.project
            )

            # 6. 清理尾部空字段
            summarized = SummarizationService._cleanup_empty_tail_fields(summarized)

            summarized = SummarizationService.sanitize_experience_data(summarized)

            return summarized

        except HTTPException:
            raise
        except Exception as e:
            error_detail = f"简历摘要优化失败: {str(e)}"
            print(f"[Summarization Error] {error_detail}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_detail)
