from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pptx import Presentation
from pptx.util import Cm

from app.schemas.resume import ResumeData
from app.services.smart_filler_service import PageConstraints, SmartFillerService


def _project_module():
    prs = Presentation(SmartFillerService.get_template_path("new_en"))
    module = next(
        candidate for candidate in SmartFillerService.collect_all_modules(prs)
        if candidate.name == "project"
    )
    return prs, module


def test_oversized_project_is_split_into_page_sized_continuations():
    _, module = _project_module()
    task_lines = [
        f"Responsibility {index}: " + "validate product requirements and delivery " * 8
        for index in range(1, 21)
    ]
    item = {
        "company": "Audi China",
        "period": "2023/01 - 2023/04",
        "name": "Tencent Service",
        "role": "Product Manager",
        "tasks": "\n".join(task_lines),
    }
    available_height = int(Cm(20))

    chunks = SmartFillerService._split_oversized_item(
        module,
        item,
        SmartFillerService.build_replacements(ResumeData(language="EN").model_dump()),
        available_height,
    )

    assert len(chunks) > 1
    assert [line for chunk in chunks for line in chunk["tasks"].splitlines()] == [
        line.strip() for line in task_lines
    ]
    assert all(chunk["company"] == item["company"] for chunk in chunks)
    assert all(chunk["name"] == item["name"] for chunk in chunks)
    template_row = next(
        row for row in module.table.rows
        if any("{{project." in cell.text for cell in row.cells)
    )
    assert all(
        SmartFillerService.estimate_row_height(
            template_row, module.table, {}, chunk, "project", 0
        ) <= available_height
        for chunk in chunks
    )


def test_splitter_keeps_commas_inside_responsibility_sentences():
    _, module = _project_module()
    task_lines = [
        "Led discovery, aligned stakeholders, and documented the delivery decision.",
        "Reviewed requirements, validated dependencies, and closed release risks.",
        "Tracked metrics, analyzed feedback, and improved the product workflow.",
    ]
    item = {
        "company": "Audi China",
        "period": "2023/01 - 2023/04",
        "name": "Tencent Service",
        "role": "Product Manager",
        "tasks": "\n".join(task_lines),
    }
    template_row = next(
        row for row in module.table.rows
        if any("{{project." in cell.text for cell in row.cells)
    )
    first_only = dict(item, tasks=task_lines[0])
    single_height = SmartFillerService.estimate_row_height(
        template_row, module.table, {}, first_only, "project", 0
    )
    combined_height = SmartFillerService.estimate_row_height(
        template_row, module.table, {}, item, "project", 0
    )
    available_height = (single_height + combined_height) // 2

    chunks = SmartFillerService._split_oversized_item(
        module, item, {}, available_height
    )

    assert len(chunks) > 1
    assert [line for chunk in chunks for line in chunk["tasks"].splitlines()] == task_lines

def test_project_fill_removes_unused_rows_and_blank_paragraphs():
    _, module = _project_module()
    template_row_idx = next(
        index for index, row in enumerate(module.table.rows)
        if any("{{project." in cell.text for cell in row.cells)
    )
    template_row = module.table.rows[template_row_idx]
    template_row.cells[len(template_row.cells) - 1].text_frame.add_paragraph()
    template_row.cells[len(template_row.cells) - 1].text_frame.add_paragraph()
    module.table._tbl.append(deepcopy(template_row._tr))
    module.table._tbl.append(deepcopy(template_row._tr))

    SmartFillerService.fill_module_data(
        module,
        [{
            "company": "Audi China",
            "period": "2023/01 - 2023/04",
            "name": "Tencent Service",
            "role": "Product Manager",
            "tasks": "Delivered one clear project outcome",
        }],
        {"{{language}}": "EN"},
        0,
        1,
    )

    assert len(module.table.rows) == template_row_idx + 1
    assert all(any(cell.text.strip() for cell in row.cells) for row in module.table.rows)
    assert all(
        len(cell.text_frame.paragraphs) == 1
        or cell.text_frame.paragraphs[-1].text.strip()
        for row in module.table.rows
        for cell in row.cells
    )
    assert module.shape.height == sum(row.height for row in module.table.rows)


def test_skill_module_stays_above_footer_safe_boundary():
    resume = ResumeData(
        language="EN",
        project=[{
            "company": "Printfleet Inc.",
            "period": "2015.03 - 2017.07",
            "name": "DCA & PFO & QuickAccessKey",
            "role": "Product Manager",
            "tasks": "Delivered product improvements",
        }],
        tech_skills="; ".join(
            f"Product Capability {index}" for index in range(24)
        ),
        lang_skills="English; Chinese",
        lang_skills_level=(
            "Fluent in English for business communication; Native Chinese speaker"
        ),
    )
    prs = Presentation(SmartFillerService.get_template_path("new_en"))
    modules = SmartFillerService.collect_all_modules(prs)

    SmartFillerService._smart_pagination_fill(
        prs,
        modules,
        SmartFillerService._prepare_module_data(resume.model_dump(), modules),
        SmartFillerService.build_replacements(resume.model_dump()),
    )

    skill_modules = [
        module
        for index, slide in enumerate(prs.slides)
        for module in SmartFillerService.collect_modules_on_slide(slide, index)
        if module.name == "skill"
    ]
    assert len(skill_modules) == 1
    assert skill_modules[0].bottom <= PageConstraints.LAST_PAGE_BOTTOM
