from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from docx import Document
from docx.text.paragraph import Paragraph

from app.core.config import BACKEND_DIR, settings
from app.schemas.jd_conversion import JDContent, JDOutputLanguage
from app.services.pdf_converter import PdfConverterService


class JDDocumentService:
    TEMPLATE_FILES = {
        "CN": "JD_Template_CN.docx",
        "EN": "JD_Template_EN.docx",
        "CNEN": "JD_Template_CNEN.docx",
    }

    REQUIREMENT_ORDER = (
        "education",
        "experience",
        "required_skills",
        "language",
        "preferred",
        "soft_skills",
    )

    @staticmethod
    def _template_path(language: JDOutputLanguage) -> Path:
        path = BACKEND_DIR / "templates" / JDDocumentService.TEMPLATE_FILES[language]
        if not path.exists():
            raise FileNotFoundError(f"JD template not found: {path}")
        return path

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join((value or "").replace("\xa0", " ").split())

    @classmethod
    def region_only_location(cls, value: str) -> str:
        location = cls._clean_text(value)
        if not location:
            return ""

        location = re.sub(
            r"(?i)\b(?:people'?s\s+republic\s+of\s+china|p\.?\s*r\.?\s*china|prc|china)\b",
            "",
            location,
        )
        location = location.replace("\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd", "").replace("\u4e2d\u56fd", "")
        location = re.sub(
            r"(?i)\b(?:on[\s-]?site|onsite|remote|hybrid)\b"
            r"|(?:\u73b0\u573a\u529e\u516c|\u8fdc\u7a0b\u529e\u516c|\u6df7\u5408\u529e\u516c)",
            "",
            location,
        )
        location = re.sub(r"\(\s*\)|\uff08\s*\uff09", "", location)
        location = re.sub(r"\s*[,\uff0c;\uff1b/|\uff5c]+\s*", " ", location)
        return cls._clean_text(location).strip(" ,\uff0c;\uff1b/|\uff5c-")

    @staticmethod
    def _find_paragraph(document, text: str) -> Paragraph:
        expected = JDDocumentService._clean_text(text)
        for paragraph in document.paragraphs:
            if JDDocumentService._clean_text(paragraph.text) == expected:
                return paragraph
        raise ValueError(f"JD template heading not found: {text}")

    @staticmethod
    def _set_paragraph_text(paragraph: Paragraph, text: str) -> None:
        source_rpr = None
        if paragraph.runs and paragraph.runs[0]._r.rPr is not None:
            source_rpr = deepcopy(paragraph.runs[0]._r.rPr)
        paragraph.clear()
        run = paragraph.add_run(text)
        if source_rpr is not None:
            run._r.insert(0, source_rpr)

    @staticmethod
    def _set_location_text(paragraph: Paragraph, text: str) -> None:
        drawing_runs = [
            deepcopy(run._r)
            for run in paragraph.runs
            if run._r.xpath(".//w:drawing") or run._r.xpath(".//w:pict")
        ]
        source_rpr = None
        for run in reversed(paragraph.runs):
            if run.text and run._r.rPr is not None:
                source_rpr = deepcopy(run._r.rPr)
                break

        paragraph.clear()
        for drawing_run in drawing_runs:
            paragraph._p.append(drawing_run)
        run = paragraph.add_run(f" {text}" if drawing_runs else text)
        if source_rpr is not None:
            run._r.insert(0, source_rpr)

    @staticmethod
    def _clone_with_text(sample: Paragraph, text: str):
        element = deepcopy(sample._p)
        paragraph = Paragraph(element, sample._parent)
        JDDocumentService._set_paragraph_text(paragraph, text)
        return element

    @staticmethod
    def _replace_segment(
        document,
        start_text: str,
        end_text: str,
        items: list[str],
        *,
        blank_before_end: bool = False,
    ) -> None:
        start = JDDocumentService._find_paragraph(document, start_text)
        end = JDDocumentService._find_paragraph(document, end_text)
        paragraphs = document.paragraphs
        start_index = next(i for i, paragraph in enumerate(paragraphs) if paragraph._p is start._p)
        end_index = next(i for i, paragraph in enumerate(paragraphs) if paragraph._p is end._p)
        if end_index <= start_index:
            raise ValueError(f"Invalid JD template section: {start_text} -> {end_text}")

        between = paragraphs[start_index + 1:end_index]
        sample = next((p for p in between if JDDocumentService._clean_text(p.text)), None)
        if sample is None:
            raise ValueError(f"JD template section has no bullet style: {start_text}")

        for paragraph in between:
            paragraph._element.getparent().remove(paragraph._element)

        for item in items:
            value = JDDocumentService._clean_text(item)
            if value:
                end._p.addprevious(JDDocumentService._clone_with_text(sample, value))

        if blank_before_end:
            # Reuse the template's empty paragraph so its spacing stays consistent.
            blank = next((p for p in between if not JDDocumentService._clean_text(p.text)), None)
            blank_element = (
                deepcopy(blank._p)
                if blank is not None
                else JDDocumentService._clone_with_text(end, "")
            )
            end._p.addprevious(blank_element)

    @staticmethod
    def _requirements(content: JDContent, language: Literal["CN", "EN"]) -> list[str]:
        items: list[str] = []
        for key in JDDocumentService.REQUIREMENT_ORDER:
            group = getattr(content.requirements, key)
            items.extend(group.cn if language == "CN" else group.en)
        return items

    @staticmethod
    def _safe_filename_part(value: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value or "JD")
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
        return (cleaned or "JD")[:80]

    @classmethod
    def generate(cls, content: JDContent, language: JDOutputLanguage) -> dict:
        document = Document(cls._template_path(language))
        location_cn = cls.region_only_location(content.location_cn)
        location_en = cls.region_only_location(content.location_en)

        if language == "CN":
            cls._set_paragraph_text(document.paragraphs[0], content.title_cn or content.title_en)
            cls._set_location_text(document.paragraphs[1], location_cn or location_en)
            cls._replace_segment(
                document,
                "岗位职责：",
                "任职要求：",
                content.responsibilities_cn,
                blank_before_end=True,
            )
            cls._replace_segment(document, "任职要求：", "Our offer:", cls._requirements(content, "CN"))
            display_title = content.title_cn or content.title_en
        elif language == "EN":
            cls._set_paragraph_text(document.paragraphs[0], content.title_en or content.title_cn)
            cls._set_location_text(document.paragraphs[1], location_en or location_cn)
            cls._replace_segment(
                document,
                "Your Tasks:",
                "Your Skills:",
                content.responsibilities_en,
                blank_before_end=True,
            )
            cls._replace_segment(document, "Your Skills:", "Our offer:", cls._requirements(content, "EN"))
            display_title = content.title_en or content.title_cn
        else:
            cls._set_paragraph_text(document.paragraphs[0], content.title_en or content.title_cn)
            cls._set_paragraph_text(document.paragraphs[1], content.title_cn or content.title_en)
            location = " ".join(filter(None, [location_en, location_cn]))
            cls._set_location_text(document.paragraphs[2], location)
            cls._replace_segment(document, "Your Tasks:", "岗位职责：", content.responsibilities_en)
            cls._replace_segment(
                document,
                "岗位职责：",
                "Your Skills:",
                content.responsibilities_cn,
                blank_before_end=True,
            )
            cls._replace_segment(document, "Your Skills:", "任职要求：", cls._requirements(content, "EN"))
            cls._replace_segment(document, "任职要求：", "Our offer:", cls._requirements(content, "CN"))
            display_title = content.title_en or content.title_cn

        output_dir = settings.output_path
        output_dir.mkdir(parents=True, exist_ok=True)
        task_output_dir = Path(tempfile.mkdtemp(prefix="jd_output_", dir=str(output_dir)))
        date_stamp = datetime.now().strftime("%Y%m%d")
        language_label = "CN+EN" if language == "CNEN" else language
        stem = f"JD_IAV-CN_{cls._safe_filename_part(display_title)}_{language_label}_{date_stamp}"
        docx_path = task_output_dir / f"{stem}.docx"
        document.save(docx_path)

        pdf_path = cls._convert_docx_to_pdf(docx_path)
        return {
            "filename": docx_path.name,
            "docx_path": str(docx_path),
            "pdf_path": str(pdf_path) if pdf_path else None,
            "pdf_available": bool(pdf_path),
        }

    @staticmethod
    def _convert_docx_to_pdf(docx_path: Path) -> Optional[Path]:
        soffice = PdfConverterService.find_libreoffice()
        if not soffice:
            return None

        work_dir = Path(tempfile.mkdtemp(prefix="iav_jd_pdf_"))
        source_path = work_dir / "jd.docx"
        generated_pdf = work_dir / "jd.pdf"
        profile_dir = work_dir / "lo_profile"
        destination = docx_path.with_suffix(".pdf")
        shutil.copy2(docx_path, source_path)
        try:
            result = subprocess.run(
                [
                    soffice,
                    f"-env:UserInstallation={profile_dir.as_uri()}",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(work_dir),
                    str(source_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "HOME": os.path.expanduser("~")},
            )
            if result.returncode != 0 or not generated_pdf.exists():
                return None
            shutil.copy2(generated_pdf, destination)
            return destination
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
