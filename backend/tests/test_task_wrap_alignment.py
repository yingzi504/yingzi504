from pathlib import Path
import sys

from pptx import Presentation


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.smart_filler_service import SmartFillerService


NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
TEMPLATE = BACKEND / "templates" / "New_Template_IAV_Resume_EN.pptx"


def test_en_task_wrap_starts_after_literal_bullet():
    prs = Presentation(TEMPLATE)
    module = next(
        module
        for module in SmartFillerService.collect_all_modules(prs)
        if module.name == "work"
    )
    SmartFillerService.fill_module_data(
        module,
        [{
            "period": "2020",
            "company": "Company",
            "role": "Engineer",
            "tasks": "A long responsibility that wraps onto a second line; Another responsibility",
        }],
        {},
        0,
        1,
    )

    task_paragraphs = [
        paragraph
        for row in module.table.rows
        for cell in row.cells
        for paragraph in cell.text_frame.paragraphs
        if paragraph.text.startswith("\u2022")
    ]
    assert task_paragraphs
    for paragraph in task_paragraphs:
        props = paragraph._p.find(f"{NS}pPr")
        assert props is not None
        assert props.get("marL") == "101600"
        assert props.get("indent") == "-101600"
