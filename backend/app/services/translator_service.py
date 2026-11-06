"""
翻译服务
中英文互译，支持术语表
"""
import asyncio
from datetime import datetime
import re
import json
import logging
from functools import lru_cache
from contextvars import ContextVar
from pathlib import Path
from typing import Optional, Tuple
from fastapi import HTTPException
from app.services.llm_service import LLMService
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.core.cv_rules import CV_RULES


logger = logging.getLogger(__name__)

# Context-local so concurrent tasks and task-list children report to the right
# pipeline without changing the public translation API.
translation_repair_observer = ContextVar("translation_repair_observer", default=None)


def normalize_target_language(value: Optional[str]) -> str:
    """Normalize and validate the supported translation target languages."""
    normalized = str(value).strip().upper() if value is not None else ""
    if normalized not in ("CN", "EN"):
        raise HTTPException(
            status_code=400,
            detail="target_language must be CN or EN",
        )
    return normalized


class TranslationQualityError(Exception):
    """Raised when translated content cannot satisfy the target-language contract."""

    error_code = "TRANSLATION_QUALITY_ERROR"

    def __init__(
        self,
        target_language: str,
        field_issues: list[dict[str, str]],
        *,
        last_output_usable: bool,
    ) -> None:
        self.target_language = str(target_language or "").upper()
        self.field_issues = [
            {
                "path": str(issue.get("path") or "<unknown>"),
                "reason": str(issue.get("reason") or "translation_quality_check_failed"),
            }
            for issue in field_issues
        ]
        self.field_paths = list(dict.fromkeys(issue["path"] for issue in self.field_issues))
        self.last_output_usable = bool(last_output_usable)
        paths = ", ".join(self.field_paths)
        super().__init__(
            f"Translation quality check failed for target {self.target_language}: {paths}"
        )

    def to_detail(self) -> dict:
        return {
            "code": self.error_code,
            "message": "Translation quality check failed",
            "target_language": self.target_language,
            "field_paths": self.field_paths,
            "field_issues": self.field_issues,
            "last_output_usable": self.last_output_usable,
        }


class TranslatorService:
    """翻译服务"""

    # One initial translation plus at most two repairs; outer layers never retry.
    MAX_TRANSLATION_ATTEMPTS = CV_RULES.translation_max_attempts

    # Root and nested registries are the single source of truth for initial
    # translation, retranslation, and final auditing.
    _ROOT_TRANSLATION_FIELDS = (
        ("name", "name", "name"),
        ("position", "position", "default"),
        ("job_position", "target position", "default"),
        ("job_position_en", "English target position", "english"),
        ("technical_area", "technical area", "default"),
        ("location", "location", "default"),
        ("birth_date", "birth date", "default"),
        ("total_exp", "total_exp", "default"),
        ("summary", "summary", "default"),
        ("tech_skills", "technical skills", "technical"),
        ("lang_skills", "language skills", "default"),
        ("lang_skills_level", "language level", "default"),
        ("training_exp", "training", "default"),
    )
    _NESTED_TRANSLATION_FIELDS = {
        "education": (
            ("period", "period", "period"),
            ("school", "school", "proper_noun"),
            ("degree", "degree", "academic"),
            ("major", "major", "default"),
        ),
        "work": (
            ("company", "company", "proper_noun"),
            ("period", "period", "period"),
            ("role", "position", "default"),
            ("tasks", "work experience", "default"),
        ),
        "project": (
            ("company", "company", "proper_noun"),
            ("period", "period", "period"),
            ("name", "project", "project_name"),
            ("role", "position", "default"),
            ("tasks", "project experience", "default"),
        ),
    }
    # These values are identifiers, privacy output, metadata, or containers.
    # anonymized_name is only synchronized from a translated anonymized name;
    # anonymized_name_cn is an immutable Chinese filename/display fallback.
    _EXCLUDED_RESUME_FIELDS = frozenset({
        "anonymized_name",
        "anonymized_name_cn",
        "phone",
        "email",
        "age",
        "gender",
        "language",
        "is_anonymized",
    })

    # 可在中文简历中保留的行业词、缩写和产品标识。这些值不代表漏译；
    # 普通英文职责和职位仍由下方的可翻译词检测拦截。
    _PROTECTED_TECH_TERMS = {
        "adb", "adas", "ai", "acc", "android", "can", "canoe", "capl", "ecu", "ethernet",
        "flexray", "fmea", "gb", "hmi", "ihc", "inca", "ivis", "linux", "lin",
        "machinevision", "matlab", "mnist", "obd", "pmp", "plc", "pycharm", "python",
        "qfd", "r&d", "sap", "scrum", "simulink", "tsr", "uds", "vba", "visicheck",
        "c++", "agile", "app", "apps", "br", "epic", "grooming", "jira", "kanban",
        "os", "po", "pi", "prd", "prds", "pv/uv", "qa", "qq", "safe", "uat", "ui", "ux",
    }
    # Common resume prose that should be translated instead of being mistaken
    # for a brand or product name merely because it is capitalized.
    _CN_TRANSLATABLE_ENGLISH_WORDS = {
        "a", "an", "as", "at", "be", "by", "do", "if", "is", "it", "of", "on",
        "or", "so", "to", "up", "us", "we",
        "analysis", "and", "artificial", "business", "capabilities", "communication", "computer",
        "customer", "data", "delivered", "delivery", "design", "development", "duties",
        "engineer", "english", "experience", "finance", "for", "in", "intelligence",
        "language", "leadership", "led",
        "management", "manager", "marketing", "native", "only", "planning", "product",
        "project", "requirements", "responsibilities", "responsibility", "responsible",
        "review", "science", "skills", "software", "speaker", "technical", "testing",
        "the", "translated", "translation", "university", "with", "writing",
        "bachelor", "master", "degree", "doctor", "doctorate", "school", "college",
        "backend", "frontend", "retention",
    }
    _LATIN_TOKEN_RE = re.compile(
        r"(?<![A-Za-z0-9])"
        r"([A-Za-z][A-Za-z0-9]*(?:[+.#&/-][A-Za-z0-9+#&/-]+)*)"
        r"(?![A-Za-z0-9])"
    )

    @staticmethod
    def normalize_total_experience(resume_data: ResumeData, target_lang: str = "EN") -> str:
        """Return one canonical numeric experience value in the target language."""
        target_lang = str(target_lang or "EN").upper()
        raw = str(getattr(resume_data, "total_exp", "") or "")
        # Source-stated totals have their own reference date; do not replace
        # them with a partial timeline or silently rebase them to today.
        if re.search(r"\d", raw):
            units = {"年": "years", "个月": "months", "月": "months"}
            if target_lang == "EN":
                return re.sub(r"(\d+(?:\.\d+)?)\s*(年|个月|月)",
                              lambda m: f"{m[1]} {units[m[2]][:-1] if float(m[1]) == 1 else units[m[2]]} ", raw).strip()
            return re.sub(r"(\d+(?:\.\d+)?)\s*(years?|yrs?|months?|mos?)",
                          lambda m: m[1] + ("年" if m[2].lower().startswith(('y',)) else "个月"),
                          raw, flags=re.I).strip()
        # With no stated total, count the union of employment months.
        months = set()
        now = datetime.now()
        for item in resume_data.work:
            period = TranslatorService.normalize_period(str(item.period or ""), "EN")
            dates = re.findall(r"(?<!\d)((?:19|20)\d{2})\.(\d{2})", period)
            if not dates or any(not 1 <= int(m) <= 12 for _, m in dates):
                continue
            start = int(dates[0][0]) * 12 + int(dates[0][1])
            if "Present" in period:
                end = now.year * 12 + now.month
            elif len(dates) > 1:
                end = int(dates[1][0]) * 12 + int(dates[1][1])
            else:
                continue
            months.update(range(start, end + 1))
        if not months:
            return ""
        years, remainder = divmod(len(months), 12)
        parts = []
        for value, cn, en in ((years, "年", "year"), (remainder, "个月", "month")):
            if value:
                parts.append(f"{value}{cn}" if target_lang == "CN" else f"{value} {en}{'s' if value != 1 else ''}")
        return ("" if target_lang == "CN" else " ").join(parts)
    @staticmethod
    def normalize_period(period: str, target_lang: str = "EN") -> str:
        if not period:
            return period
        value = str(period).strip()
        target_lang = str(target_lang or "EN").upper()
        ongoing = chr(33267) + chr(20170) if target_lang == "CN" else "Present"
        months = {"jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
                  "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
                  "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
                  "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12}
        value = re.sub(r"\b(" + "|".join(months) + r")\s*(\d{4})\b",
                       lambda m: "{}.{:02d}".format(m.group(2), months[m.group(1).lower()]), value, flags=re.I)
        value = re.sub(r"(?<!\d)(\d{4})\s*" + chr(24180) + r"\s*(\d{1,2})\s*" + chr(26376),
                       lambda m: "{}.{:02d}".format(m.group(1), int(m.group(2))), value)
        value = re.sub(r"(?<!\d)(\d{4})\s*[./-]\s*(\d{1,2})(?!\d)",
                       lambda m: "{}.{:02d}".format(m.group(1), int(m.group(2))), value)
        value = re.sub(r"[~\u223c\u301c\uff5e\u2013\u2014\u2011]+", " - ", value)
        value = re.sub(r"\s*(?:" + chr(33267) + chr(20170) + "|" + chr(29616) + chr(22312) + r"|now|present|current)\s*",
                       " - " + ongoing, value, flags=re.I)
        dates = re.findall(r"(?<!\d)(\d{4})[./-](\d{1,2})(?!\d)", value)
        if len(dates) >= 2:
            return "{}.{:02d} - {}.{:02d}".format(dates[0][0], int(dates[0][1]), dates[1][0], int(dates[1][1]))
        if len(dates) == 1 and ongoing in value:
            return "{}.{:02d} - {}".format(dates[0][0], int(dates[0][1]), ongoing)
        years = re.search(r"(?<!\d)(\d{4})\s*[-/]\s*(\d{4})(?!\d)", value)
        if years:
            return "{}.01 - {}.12".format(years.group(1), years.group(2))
        return re.sub(r"\s*-\s*", " - ", value).strip()
    @staticmethod
    def _has_language_residue(
        text: str,
        target_lang: str,
        field_policy: str = "default",
    ) -> bool:
        """判断译文是否仍包含目标语言不应出现的主要内容。"""
        if not text or not text.strip():
            return True
        if field_policy is True:
            field_policy = "technical"
        elif not isinstance(field_policy, str):
            field_policy = "default"
        effective_target_lang = "EN" if field_policy == "english" else target_lang
        return bool(TranslatorService._residue_fragments(
            text, effective_target_lang, field_policy
        ))

    @staticmethod
    def _residue_fragments(text: str, target_lang: str, field_policy: str) -> list[str]:
        """Return exactly the spans used by review, for actionable repair feedback."""
        if target_lang == "EN" or field_policy == "english":
            return list(dict.fromkeys(re.findall(
                r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]+", text
            )))

        # Institutions and degrees must be localized too. Casing is not
        # evidence that an English company/school name may be skipped.
        if field_policy in {"proper_noun", "academic"}:
            return list(dict.fromkeys(TranslatorService._LATIN_TOKEN_RE.findall(text)))

        residues = []
        has_chinese = bool(re.search(r"[\u3400-\u9fff]", text))
        for token in TranslatorService._LATIN_TOKEN_RE.findall(text):
            normalized = token.lower().rstrip(".")
            if normalized in TranslatorService._PROTECTED_TECH_TERMS:
                continue
            # Two-letter department/region codes in Chinese prose are identifiers,
            # just like longer acronyms. English function words remain residue;
            # a standalone role such as PM still requires translation.
            if (has_chinese and re.fullmatch(r"[A-Z]{2}", token)
                    and (normalized not in TranslatorService._CN_TRANSLATABLE_ENGLISH_WORDS
                         or token in {"IT", "US"})):
                continue
            if TranslatorService._is_strict_technical_identifier(token):
                continue
            if (TranslatorService._is_preservable_proper_token(token)
                    and (field_policy != "project_name"
                         or not re.fullmatch(r"[A-Z][a-z]+", token))):
                continue
            residues.append(token)
        return list(dict.fromkeys(residues))

    @staticmethod
    async def _wait_for_repair(attempt: int, path: str, reason: str) -> None:
        observer = translation_repair_observer.get()
        if observer is not None:
            observer(path, attempt, reason)
        # Keep bounded repairs cancellable and yield to concurrent tasks.
        await asyncio.sleep(min(5.0, max(0, attempt - 2)))

    @staticmethod
    def _is_preservable_proper_token(token: str) -> bool:
        """Recognize acronym/brand-shaped tokens without accepting prose."""
        normalized = str(token or "").lower().rstrip(".")
        if normalized in TranslatorService._CN_TRANSLATABLE_ENGLISH_WORDS:
            return False
        letters = re.sub(r"[^A-Za-z]", "", str(token or ""))
        if not letters:
            return True
        if letters.isupper() and (len(letters) >= 3 or len(letters) == 1):
            return True
        if re.fullmatch(r"[A-Z][a-z]{3,}", token):
            return True
        if re.search(r"[A-Z].*[A-Z]", token) and not token.isupper():
            return True
        return False

    @staticmethod
    def _is_strict_technical_identifier(token: str) -> bool:
        """Allow alphanumeric model/protocol identifiers."""
        return bool(
            re.fullmatch(
                r"(?=.*\d)[A-Za-z][A-Za-z0-9]*(?:[-_/][A-Za-z0-9]+)*",
                token,
            )
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def _term_base_entries() -> tuple[tuple[str, str], ...]:
        term_base_path = Path(__file__).resolve().parents[2] / "data" / "term_base.json"
        try:
            payload = json.loads(term_base_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return ()
        entries = []
        for item in payload.get("terms", []):
            if not isinstance(item, dict):
                continue
            cn = str(item.get("cn") or "").strip()
            en = str(item.get("en") or "").strip()
            if cn and en:
                entries.append((cn, en))
        return tuple(entries)

    @classmethod
    def _term_base_prompt(cls, target_lang: str) -> str:
        entries = cls._term_base_entries()
        if not entries:
            return ""
        mappings = (
            (f"{en} -> {cn}" for cn, en in entries)
            if target_lang == "CN"
            else (f"{cn} -> {en}" for cn, en in entries)
        )
        return "\n术语库（严格使用以下目标语言映射）：\n" + "\n".join(mappings)

    @staticmethod
    def _infer_resume_language(resume_data: ResumeData) -> str:
        """从实际字段内容推断源语言，避免依赖 LLM 可能填错的 language 字段。"""
        values = []
        for field in (
            "name", "position", "technical_area", "total_exp", "location", "summary",
            "tech_skills", "lang_skills", "lang_skills_level", "training_exp",
        ):
            value = getattr(resume_data, field, None)
            if value:
                values.append(str(value))
        for item in (*resume_data.education, *resume_data.work, *resume_data.project):
            values.extend(
                str(getattr(item, field, "") or "")
                for field in ("company", "period", "school", "degree", "major", "role", "name", "tasks")
            )
        text = " ".join(values)
        chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
        latin_count = len(re.findall(r"[A-Za-z]{2,}", text))
        return "CN" if chinese_count >= latin_count else "EN"

    @staticmethod
    def _translation_fields(resume_data: ResumeData):
        for attr, context, field_policy in TranslatorService._ROOT_TRANSLATION_FIELDS:
            yield (attr, resume_data, attr, context, field_policy)
        for collection_name, field_specs in (
            TranslatorService._NESTED_TRANSLATION_FIELDS.items()
        ):
            for idx, item in enumerate(getattr(resume_data, collection_name)):
                for attr, context, field_policy in field_specs:
                    yield (
                        f"{collection_name}[{idx}].{attr}",
                        item,
                        attr,
                        context,
                        field_policy,
                    )

    @staticmethod
    def _period_is_standard(value: str, target_lang: str) -> bool:
        ongoing = "至今" if str(target_lang).upper() == "CN" else "Present"
        return bool(re.fullmatch(r"\d{4}\.\d{2} - (?:\d{4}\.\d{2}|" + re.escape(ongoing) + r")", str(value or "").strip()))

    @classmethod
    def _audit_translation_issues(
        cls, resume_data: ResumeData, target_lang: str
    ) -> list[dict[str, str]]:
        issues = []
        for path, obj, attr, context, field_policy in cls._translation_fields(resume_data):
            value = getattr(obj, attr, None)
            if not value:
                continue
            value = str(value)
            if attr == "period":
                # Free-form dates (e.g. a single year) cannot be repaired by
                # inventing a date range. Only actual language residue needs LLM.
                if cls._has_language_residue(value, target_lang, field_policy):
                    issues.append({"path": path, "reason": "source_language_residue"})
            elif cls._has_language_residue(value, target_lang, field_policy):
                issues.append({"path": path, "reason": "source_language_residue"})
        return issues

    @classmethod
    def audit_translation(cls, resume_data: ResumeData, target_lang: str) -> list[str]:
        return [
            issue["path"]
            for issue in cls._audit_translation_issues(resume_data, target_lang)
        ]

    @classmethod
    async def review_and_retranslate(cls, resume_data: ResumeData, target_lang: str) -> ResumeData:
        """Compatibility entry point for advisory final review; never retries."""
        target_lang = str(target_lang or "").upper()
        if target_lang not in ("CN", "EN"):
            return resume_data
        reviewed = resume_data.model_copy(deep=True)
        cls._normalize_resume_periods(reviewed, target_lang)
        # Advisory only: an incomplete term base must not block file generation
        # or restart an exhausted field-level repair budget.
        issues = cls.audit_translation(reviewed, target_lang)
        if issues:
            logger.warning(
                "Translation requires manual review; target=%s fields=%s; continuing output",
                target_lang, issues,
            )
        return reviewed

    @staticmethod
    def _normalize_resume_periods(resume_data: ResumeData, target_lang: str) -> None:
        for item in (*resume_data.education, *resume_data.work, *resume_data.project):
            if item.period:
                item.period = TranslatorService.normalize_period(item.period, target_lang)

    @staticmethod
    def _task_items(text: str) -> list[str]:
        """Split a task block into independent items while retaining every item."""
        if not text or not text.strip():
            return []
        value = str(text).replace("\r\n", "\n").strip()
        item_prefix = re.compile(
            r"^\s*(?:"
            r"\(\d+\)\s+"
            r"|\d+[.)]\s+"
            r"|[•·▪▸►●○◆◇❖➢✓✔☑▫\-*\u2022\u2023\u25e6\u2043\u2219]\s*"
            r")"
        )
        parts = [
            part.strip()
            for part in re.split(r"[\n;；]+", value)
            if part.strip()
        ]
        items = [item_prefix.sub("", part).strip() for part in parts]
        return [item for item in items if item]

    @staticmethod
    async def _translate_task_list(
        text: str,
        source_lang: str,
        target_lang: str,
        context: str,
        field_path: Optional[str] = None,
        field_policy: str = "default",
    ) -> str:
        """Translate each task independently so one model response cannot drop siblings."""
        items = TranslatorService._task_items(text)
        if not items:
            return text

        async def translate_item(index, source_item):
            item_path = (
                f"{field_path}[{index}]"
                if field_path and len(items) > 1
                else (field_path or f"<tasks>[{index}]")
            )
            result = await TranslatorService.translate_text(
                source_item, source_lang, target_lang, context=context,
                field_path=item_path, field_policy=field_policy,
            )
            cleaned = result.strip() if isinstance(result, str) else ""
            return cleaned or source_item

        # Each child owns its bounded repair budget; preserve all sibling items.
        # A provider error/cancellation must not leave background calls alive.
        pending = [
            asyncio.create_task(translate_item(index, item))
            for index, item in enumerate(items)
        ]
        try:
            validated_items = await asyncio.gather(*pending)
        finally:
            for task in pending:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        return ";\n".join(validated_items)
    
    # 常见单位翻译映射
    UNIT_TRANSLATIONS = {
        "CN": {
            "年": "years",
            "个月": "months",
            "月": "months",
            "天": "days",
            "小时": "hours"
        },
        "EN": {
            "years": "年",
            "year": "年",
            "months": "个月",
            "month": "个月",
            "days": "天",
            "day": "天",
            "hours": "小时",
            "hour": "小时"
        }
    }
    
    @staticmethod
    def _translate_units(text: str, source_lang: str, target_lang: str) -> str:
        """
        翻译常见单位
        
        Args:
            text: 文本
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            处理后的文本
        """
        if source_lang not in TranslatorService.UNIT_TRANSLATIONS:
            return text
            
        unit_map = TranslatorService.UNIT_TRANSLATIONS[source_lang]
        
        for unit, translation in unit_map.items():
            # 使用正则确保只匹配完整的单位
            pattern = r'(\d+)\s*' + re.escape(unit) + r'\b'
            replacement = r'\1 ' + translation
            text = re.sub(pattern, replacement, text)
            
        return text
    
    @staticmethod
    def _clean_translation_result(text: str, target_lang: str) -> str:
        """
        清理翻译结果，移除多余的标记
        
        Args:
            text: 翻译结果
            target_lang: 目标语言
            
        Returns:
            清理后的文本
        """
        value = str(text or "").strip()
        lines = value.splitlines()
        fence_pattern = re.compile(
            r"^```(?:text|markdown|md)?\s*$", re.IGNORECASE
        )
        if lines and fence_pattern.fullmatch(lines[0].strip()):
            lines.pop(0)
        if lines and lines[-1].strip() == "```":
            lines.pop()

        exact_titles = {
            "translation",
            "translation result",
            "translated text",
            "译文",
            "翻译",
            "翻译结果",
        }
        if lines:
            candidate = re.sub(r"^#{1,6}\s+", "", lines[0].strip())
            candidate = candidate.rstrip(":：").strip().lower()
            if candidate in exact_titles:
                lines.pop(0)

        return "\n".join(lines).strip()
    
    @staticmethod
    async def translate_text(
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
        field_path: Optional[str] = None,
        field_policy: str = "default",
    ) -> str:
        """
        翻译单个文本
        """
        try:
            target_lang = normalize_target_language(target_lang)
            if not text or not text.strip():
                return text
            
            # Direct callers get the same policy as registered resume fields.
            if field_policy == "default":
                field_policy = {
                    "company": "proper_noun", "school": "proper_noun",
                    "degree": "academic", "project": "project_name",
                }.get(context, field_policy)

            # 以目标语言残留检测为准，不依赖“包含一个中文字符就判定为中文”的旧逻辑。
            # 这样公司名、职位名和职责中的中英混合内容也会继续翻译。
            if not TranslatorService._has_language_residue(
                text, target_lang, field_policy
            ):
                logger.debug(
                    "Translation skipped; target=%s field=%s",
                    target_lang,
                    field_path or context or "<text>",
                )
                return text

            # 源语言字段可能由 LLM 填错；当目标语言明确时，用残留字符确定翻译方向。
            actual_source = "EN" if target_lang == "CN" else "CN"
            
            source_desc = "中文" if actual_source == "CN" else "英文"
            target_desc = "中文" if target_lang == "CN" else "英文"
            
            # 先尝试单位翻译（针对"9年"这种简单情况）
            if context == "工作经验" or context == "total_exp" or context == "工作经验年限":
                unit_translated = TranslatorService._translate_units(text, actual_source, target_lang)
                if unit_translated != text:
                    # 检查是否完全处理了
                    if not TranslatorService._has_language_residue(
                        unit_translated, target_lang, field_policy
                    ):
                        logger.debug(
                            "Translation completed by unit mapping; target=%s field=%s",
                            target_lang,
                            field_path or context or "<text>",
                        )
                        return unit_translated
            
            # 构建更好的提示词，确保完整翻译
            system_prompt = f"""你是一个专业的简历翻译专家，专门从事{source_desc}到{target_desc}的简历翻译。

翻译要求：
1. 保持简历的专业和正式风格
2. 技术术语翻译准确，符合行业标准
3. 保持原有格式和结构（包括换行、标点符号等）
4. 完整翻译所有内容，不要遗漏任何词语或部分
5. 翻译要自然流畅，符合{target_desc}的表达习惯
6. 只返回翻译结果，不要添加任何其他说明、标题或解释
7. 不要添加markdown格式或标题

关键翻译规则：
- "至今" → "Present"（英译中）或 "至今"（保持）
- "至" → "to" 或 "-"（英译中时）
- 数字+单位要完整翻译为{target_desc}（如 "9年"→"9 years"，"3个月"→"3 months"）
- 所有自然语言字段统一翻译为{target_desc}，包括公司、学校、学院、项目名称、学位、专业和职责；不得因为是专有名词而跳过翻译
- 公司、学校、学院名称优先使用已知官方目标语言名称，其次使用通行译名；没有可靠译名时采用合理音译或意译，不得编造官方身份、法人全称、地区或隶属关系
- 保留原始信息是保持事实和实体身份，不是保留原文语言；中文机构名称和学位仅输出中文，不附加英文原名。Master Degree、Bachelor 等必须翻译
- 项目名称中的业务描述必须翻译；技术缩写、产品标识、工具名、协议名、型号以及正文中的部门/地区代码可以保留，不得据此保留整个英文标题
- 对于语言技能列表（如"英语（流利）、日语（基础）"），完整翻译所有语言名称和水平描述
- 职位名称要符合{target_desc}职场习惯
- 工作内容描述保持专业性和动词时态的一致性
- 技术术语使用行业标准译法"""
            system_prompt += TranslatorService._term_base_prompt(target_lang)

            # 添加上下文信息（如果有）
            context_text = f"\n\n上下文信息：这是简历中的「{context}」部分。" if context else ""
            
            user_prompt = f"""请将以下{source_desc}内容完整翻译为{target_desc}：

{text}{context_text}

请确保：
1. 完整翻译所有内容，不要遗漏任何词语或句子
2. 保留已有正确译文；公司名、学校名、学院名、项目业务描述和学位仍必须翻译，不能因首字母大写或属于外国机构而保留原文
3. 保持专业、正式的简历语气
4. 对于时间范围（如 "2021-03 至 至今"），完整翻译为{target_desc}格式（如 "2021-03 to Present"）
5. 只返回翻译结果，不要添加任何标题、标记或说明"""
            
            translated_text = ""
            latest_nonempty = text
            repair_prompt = user_prompt
            for attempt in range(1, TranslatorService.MAX_TRANSLATION_ATTEMPTS + 1):
                try:
                    translated_text = await LLMService.call_llm(
                        prompt=repair_prompt,
                        system_prompt=system_prompt,
                        temperature=0.2 if attempt == 1 else 0.1,
                        max_tokens=3000
                    )
                except Exception:
                    if attempt == 1:
                        raise
                    logger.warning(
                        "Translation repair unavailable; target=%s field=%s; retaining draft",
                        target_lang, field_path or context or "<text>",
                    )
                    return latest_nonempty
                translated_text = TranslatorService._clean_translation_result(
                    translated_text if isinstance(translated_text, str) else "", target_lang
                )
                if not TranslatorService._has_language_residue(
                    translated_text, target_lang, field_policy
                ):
                    return translated_text
                if translated_text.strip():
                    latest_nonempty = translated_text
                last_failure_reason = (
                    "source_language_residue"
                    if translated_text.strip()
                    else "empty_model_output"
                )
                logger.warning(
                    "Translation quality repair; target=%s field=%s attempt=%s reason=%s",
                    target_lang,
                    field_path or context or "<text>",
                    attempt,
                    last_failure_reason,
                )
                if attempt >= TranslatorService.MAX_TRANSLATION_ATTEMPTS:
                    logger.warning(
                        "Translation repair limit reached; target=%s field=%s; retaining draft for manual review",
                        target_lang, field_path or context or "<text>",
                    )
                    return latest_nonempty
                fragments = TranslatorService._residue_fragments(
                    latest_nonempty, target_lang, field_policy
                )
                repair_prompt = f"""请修复上一轮译文并返回完整的{target_desc}结果。字段：{field_path or context or '<text>'}
复核原因：{last_failure_reason}
原文（用于核对事实、数字和条目，不可删减或虚构）：
{text}

上一轮非空译文：
{latest_nonempty}

本轮待翻译残留：{json.dumps(fragments, ensure_ascii=False)}
保留已正确翻译的内容，逐一翻译上述残留；结合上下文复核整段。
机构名称和学位必须使用目标语言；未知机构名称采用合理音译或意译，不编造机构事实。项目业务描述必须翻译；仅技术缩写、产品标识、工具名、协议名、型号和正文中的部门/地区代码可保留。
不可通过删除残留或返回空白来通过复核。只返回完整修复后的译文。"""
                await TranslatorService._wait_for_repair(
                    attempt, field_path or context or "<text>", last_failure_reason
                )
            
        except (HTTPException, TranslationQualityError):
            raise
        except Exception as e:
            error_detail = f"翻译失败: {type(e).__name__}"
            logger.error(
                "Translation call failed; target=%s field=%s error_type=%s",
                target_lang,
                field_path or context or "<text>",
                type(e).__name__,
            )
            raise HTTPException(status_code=500, detail=error_detail)
    
    @staticmethod
    async def _translate_name(
        name: str,
        source_lang: str,
        target_lang: str,
        gender: Optional[str] = None
    ) -> str:
        """
        翻译姓名/敬称（保证英文版输出无中文残留）

        规则优先级：
        1. 中文敬称格式（如 "赵先生"/"李女士"）→ 英文敬称 "Mr. Zhao"/"Ms. Li"（规则转换，稳定可靠）
        2. 英文敬称格式（如 "Mr. Zhao"）→ 目标为英文时已满足，直接返回
        3. 其他中文姓名 → 调用 LLM 翻译兜底

        Args:
            name: 当前姓名文本
            source_lang: 源语言 ("CN"/"EN")
            target_lang: 目标语言 ("CN"/"EN")
            gender: 性别 male/female（用于英文敬称推断，缺失时默认 male）

        Returns:
            翻译后的姓名
        """
        if not name or not name.strip():
            return name

        name = name.strip()

        # ── 目标英文：中文敬称格式 → 英文敬称格式 ──
        if target_lang == "EN":
            # 中文敬称是后缀：赵先生 / 李女士 / 王小姐 ...
            cn_honorifics = (
                ('女士', True), ('小姐', True), ('夫人', True), ('太太', True),
                ('先生', False),
            )
            for suffix, is_female in cn_honorifics:
                if name.endswith(suffix):
                    surname_cn = name[:-len(suffix)]
                    if not surname_cn:
                        return name
                    # 局部导入避免循环依赖
                    from app.services.anonymizer_service import AnonymizerService
                    surname_pinyin = AnonymizerService._chinese_name_to_pinyin(surname_cn)
                    prefix = 'Ms.' if is_female else 'Mr.'
                    return f"{prefix} {surname_pinyin}"

            # 已是英文敬称格式，直接返回
            if re.match(r'^(Mr\.|Ms\.|Mrs\.|Miss)\s+', name):
                return name

        # ── 目标中文：英文敬称格式 → 中文敬称格式（拼音反查有限，仅尝试姓氏映射）──
        if target_lang == "CN":
            # 中文敬称已是目标语言
            if any(name.endswith(s) for s in ('先生', '女士', '小姐', '夫人', '太太')):
                return name

        # ── 兜底：调用 LLM 翻译（如未脱敏的中文全名 "赵伟" → "Zhao Wei"）──
        if source_lang != target_lang:
            try:
                translated = await TranslatorService.translate_text(
                    name, source_lang, target_lang, context="姓名", field_path="name"
                )
                if translated and translated.strip():
                    return translated.strip()
            except TranslationQualityError:
                raise
            except Exception as e:
                logger.warning(
                    "Name translation fallback; target=%s field=name error_type=%s",
                    target_lang,
                    type(e).__name__,
                )

        return name

    @staticmethod
    async def translate_resume(resume_data: ResumeData, target_lang: str) -> ResumeData:
        """
        翻译整个简历（Pipeline步骤3的一部分）
        
        Args:
            resume_data: 原始简历数据
            target_lang: 目标语言 ("CN" 或 "EN")
            
        Returns:
            翻译后的简历数据
        """
        try:
            target_lang = normalize_target_language(target_lang)
            
            translated = resume_data.model_copy(deep=True)
            original_name = translated.name
            original_anonymized_name = translated.anonymized_name
            translated.language = target_lang

            for path, obj, attr, context, field_policy in (
                TranslatorService._translation_fields(translated)
            ):
                value = getattr(obj, attr, None)
                if not value:
                    continue
                field_target_lang = (
                    "EN" if field_policy == "english" else target_lang
                )
                field_source_lang = (
                    "EN" if field_target_lang == "CN" else "CN"
                )
                if path == "name":
                    if (
                        target_lang == "CN"
                        and translated.anonymized_name_cn
                        and re.search(
                            r"[\u4e00-\u9fff]", translated.anonymized_name_cn
                        )
                    ):
                        result = translated.anonymized_name_cn
                    else:
                        result = await TranslatorService._translate_name(
                            str(value),
                            field_source_lang,
                            field_target_lang,
                            translated.gender,
                        )
                elif attr == "period":
                    result = TranslatorService.normalize_period(
                        str(value), target_lang
                    )
                elif attr in ("tasks", "tech_skills"):
                    result = await TranslatorService._translate_task_list(
                        str(value),
                        field_source_lang,
                        field_target_lang,
                        context,
                        field_path=path,
                        field_policy=field_policy,
                    )
                else:
                    result = await TranslatorService.translate_text(
                        str(value),
                        field_source_lang,
                        field_target_lang,
                        context=context,
                        field_path=path,
                        field_policy=field_policy,
                    )
                if attr == "tech_skills" and result:
                    result = result.replace("\n", " ")
                if result and result.strip():
                    setattr(obj, attr, result.strip())

            translated.total_exp = TranslatorService.normalize_total_experience(
                resume_data, target_lang
            )

            if (
                translated.is_anonymized
                and original_anonymized_name
                and original_anonymized_name == original_name
            ):
                translated.anonymized_name = translated.name

            TranslatorService._normalize_resume_periods(translated, target_lang)
            translated = await TranslatorService.review_and_retranslate(translated, target_lang)
            return translated
            
        except (HTTPException, TranslationQualityError):
            raise
        except Exception as e:
            error_detail = f"简历翻译失败: {type(e).__name__}"
            logger.error(
                "Resume translation failed; target=%s error_type=%s",
                target_lang,
                type(e).__name__,
            )
            raise HTTPException(status_code=500, detail=error_detail)
