from pathlib import Path
import sys

from pptx import Presentation


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.smart_filler_service import SmartFillerService


NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
TEMPLATE = BACKEND / "templates" / "New_Template_IAV_Resume_CN.pptx"
PROJECT_INDENT_REGRESSION_TEMPLATE = (
    BACKEND / "templates" / "af80e91a_New_Template_IAV_Resume_CN.pptx"
)


def _work_module():
    prs = Presentation(TEMPLATE)
    module = next(m for m in SmartFillerService.collect_all_modules(prs) if m.name == "work")
    return prs, module


def test_cn_template_uses_full_width_label_colons_and_11pt_work_text():
    prs, module = _work_module()
    all_text = "\n".join(
        [shape.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame]
        + [
            cell.text
            for slide in prs.slides
            for shape in slide.shapes
            if shape.has_table
            for row in shape.table.rows
            for cell in row.cells
        ]
    )
    for label in ("姓名", "技术领域", "工作经验", "职责", "能力", "语言"):
        assert f"{label}:" not in all_text
        assert f"{label}：" in all_text

    for row in module.table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    if run.text:
                        assert run.font.size is not None
                        assert run.font.size.pt == 11


def test_cn_work_output_has_11pt_text_and_left_aligned_wrap():
    _, module = _work_module()
    data = [{
        "period": "2020-至今",
        "company": "测试汽车有限公司",
        "role": "测试工程师",
        "tasks": "这是一段足够长的工作职责文本用于验证自动换行后不再产生额外左侧空白",
    }]
    SmartFillerService.fill_module_data(module, data, {}, 0, 1)

    for row in module.table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    if run.text:
                        assert run.font.size is not None
                        assert run.font.size.pt == 12
                if paragraph.text.startswith("•"):
                    props = paragraph._p.find(f"{NS}pPr")
                    assert props is not None
                    assert props.get("marL") == "101600"
                    assert props.get("indent") == "-101600"


def test_cn_project_output_has_left_aligned_wrap():
    prs = Presentation(TEMPLATE)
    module = next(m for m in SmartFillerService.collect_all_modules(prs) if m.name == "project")
    data = [{
        "period": "2022-至今",
        "company": "测试汽车有限公司",
        "role": "项目负责人",
        "name": "新车型认证项目",
        "tasks": "这是一段足够长的项目职责文本用于验证自动换行后与首行采用相同左边界",
    }]
    SmartFillerService.fill_module_data(module, data, {}, 0, 1)

    task_paragraphs = [
        paragraph
        for row in module.table.rows
        for cell in row.cells
        for paragraph in cell.text_frame.paragraphs
        if paragraph.text.startswith("•")
    ]
    assert task_paragraphs
    for paragraph in task_paragraphs:
        props = paragraph._p.find(f"{NS}pPr")
        assert props is not None
        assert props.get("marL") == "101600"
        assert props.get("indent") == "-101600"


def test_cn_project_does_not_apply_task_indent_to_regular_text():
    """普通项目文字和时间不能继承任务段落的悬挂缩进。"""
    prs = Presentation(PROJECT_INDENT_REGRESSION_TEMPLATE)
    module = next(
        m for m in SmartFillerService.collect_all_modules(prs) if m.name == "project"
    )
    SmartFillerService.fill_module_data(
        module,
        [{
            "period": "2022-至今",
            "company": "测试汽车有限公司",
            "role": "项目负责人",
            "name": "新车型认证项目",
            "tasks": "第一条项目职责文本\n第二条项目职责文本",
        }],
        {},
        0,
        1,
    )

    row = module.table.rows[0]
    regular_paragraphs = [
        paragraph
        for cell in row.cells
        for paragraph in cell.text_frame.paragraphs
        if paragraph.text and not paragraph.text.startswith("•")
    ]
    assert regular_paragraphs
    for paragraph in regular_paragraphs:
        props = paragraph._p.find(f"{NS}pPr")
        assert props is not None
        assert props.get("marL", "0") == "0"
        assert props.get("indent") == "0"


if __name__ == "__main__":
    test_cn_template_uses_full_width_label_colons_and_11pt_work_text()
    test_cn_work_output_has_11pt_text_and_left_aligned_wrap()
    test_cn_project_output_has_left_aligned_wrap()
    print("CN work template format checks passed")
