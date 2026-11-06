import asyncio
import sys
from pathlib import Path

from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.parser_service import ParserService
from app.services.anonymizer_service import AnonymizerService


def test_docx_parser_adds_header_text_to_nonempty_body(tmp_path):
    source = tmp_path / "header-name.docx"
    document = Document()
    document.add_paragraph("Skills and work experience are stored in the body.")
    document.sections[0].header.paragraphs[0].text = "Candidate Name"
    document.save(source)

    text, _ = asyncio.run(ParserService._parse_with_python_docx(str(source)))
    merged = ParserService._merge_docx_ooxml_text(
        text, ParserService._parse_docx_ooxml_text(str(source))
    )

    assert "Skills and work experience" in merged
    assert "Candidate Name" in merged
    assert merged.startswith("Candidate Name")


def test_materially_richer_ooxml_replaces_partial_parser_output():
    parsed = "Visible paragraph"
    ooxml = "\n".join(["Candidate Name", "Visible paragraph", "Textbox detail " * 20])

    assert ParserService._merge_docx_ooxml_text(parsed, ooxml) == ooxml.strip()


def test_resume_surname_has_filename_pinyin():
    assert AnonymizerService._chinese_name_to_pinyin("雍婷") == "Yong"
