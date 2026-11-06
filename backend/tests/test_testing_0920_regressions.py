import asyncio
import sys
import threading
from types import SimpleNamespace

import pytest
from pptx import Presentation
from pptx.util import Cm

from app.schemas.resume import ResumeData, ProjectItem
from app.services.llm_service import LLMService
from app.services.smart_filler_service import SmartFillerService
from app.services.summarization_service import SummarizationService


@pytest.mark.parametrize("label", ["Language Skills:", "Language:", "语言：", "语言技能："])
def test_empty_language_paragraph_keeps_other_skills_in_same_row(label):
    prs = Presentation()
    table = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_table(2, 1, Cm(1), Cm(1), Cm(15), Cm(3)).table
    table.cell(0, 0).text = "Technical skills: Rust; API design\n" + label
    table.cell(1, 0).text = "Training experience: Safety training"
    SmartFillerService._cleanup_empty_skill_labels(prs, {"{{tech_skills}}": "Rust; API design", "{{training_exp}}": "Safety training"})
    assert len(table.rows) == 2
    assert table.cell(0, 0).text == "Technical skills: Rust; API design"
    assert table.cell(1, 0).text == "Training experience: Safety training"


def test_project_duplicates_merge_but_distinct_roles_periods_and_tasks_survive():
    data = ResumeData(project=[
        ProjectItem(name="Cloud (Platform)", company="Example", period="2022.01-2023.02", role="Engineer", tasks="Build API; Validate inputs"),
        ProjectItem(name="Cloud Platform", company="Example", period="2022/01-2023/02", role="Engineer", tasks="build API; Deploy service"),
        ProjectItem(name="Cloud Platform", company="Example", period="2024.01-2024.02", role="Engineer", tasks="Migrate service"),
        ProjectItem(name="Cloud Platform", company="Other", period="2022.01-2023.02", role="Engineer", tasks="Design API"),
    ])
    result = SummarizationService.sanitize_experience_data(data)
    assert len(result.project) == 3
    assert result.project[0].tasks == "Build API;\nValidate inputs;\nDeploy service"
    assert len(data.project) == 4


def test_case_insensitive_skill_dedup_keeps_distinct_versions():
    result = SummarizationService._cleanup_empty_tail_fields(ResumeData(language="EN", tech_skills="Rust; RUST; Python 2; Python 3; API design"))
    assert result.tech_skills == "Rust; Python 2; Python 3; API design"


@pytest.mark.asyncio
async def test_slow_llm_does_not_block_event_loop(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def completion(**kwargs):
        entered.set()
        release.wait(2)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=completion))
    task = asyncio.create_task(LLMService.call_llm("test"))
    try:
        for _ in range(100):
            if entered.is_set():
                break
            await asyncio.sleep(0.01)
        assert entered.is_set()
        assert not task.done(), "synchronous completion blocked the loop"
    finally:
        release.set()
        assert await task == "ok"


def test_work_continues_into_partial_page_without_losing_tasks():
    prs = Presentation(SmartFillerService.get_template_path("new_en"))
    modules = SmartFillerService.collect_all_modules(prs)
    tasks = [f"Validate interface number {i} against documented requirements" for i in range(22)]
    data = ResumeData(language="EN", work=[
        {"company": "First employer", "role": "Engineer", "tasks": "\n".join(tasks[:12])},
        {"company": "Second employer", "role": "Engineer", "tasks": "\n".join(tasks)},
    ]).model_dump()
    replacements = SmartFillerService.build_replacements(data)
    module_data = SmartFillerService._prepare_module_data(data, modules)
    SmartFillerService._smart_pagination_fill(prs, modules, module_data, replacements)
    tables = [s.table for s in prs.slides[0].shapes if s.has_table]
    first_text = "\n".join(c.text for t in tables for r in t.rows for c in r.cells)
    assert "Second employer" in first_text
    all_text = "\n".join(c.text for slide in prs.slides for shape in slide.shapes if shape.has_table for row in shape.table.rows for c in row.cells)
    for task in tasks:
        assert task in all_text


def test_empty_language_placeholder_and_separate_label_do_not_consume_page_space():
    prs = Presentation()
    table = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_table(1, 1, Cm(1), Cm(1), Cm(15), Cm(3)).table
    table.cell(0, 0).text = "Language Skills:\n{{lang_skills}} ({{lang_skills_level}} )\nTechnical skills: {{tech_skills}}"
    SmartFillerService._cleanup_empty_skill_labels(prs, {"{{lang_skills}}": "", "{{lang_skills_level}}": "", "{{tech_skills}}": "API design"})
    assert table.cell(0, 0).text == "Technical skills: {{tech_skills}}"


def test_project_task_dedup_preserves_meaningful_symbols():
    common = dict(name="Compiler", company="Example", period="2022.01-2023.02")
    result = SummarizationService.sanitize_experience_data(ResumeData(project=[
        ProjectItem(**common, tasks="Support C"),
        ProjectItem(**common, tasks="Support C++; Support C#"),
    ]))
    assert result.project[0].tasks == "Support C;\nSupport C++;\nSupport C#"


@pytest.mark.parametrize("language", ["CN", "EN"])
def test_resume_without_skills_still_renders(monkeypatch, tmp_path, language):
    from app.services.pdf_converter import PdfConverterService
    monkeypatch.setattr(SmartFillerService, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(PdfConverterService, "is_available", lambda: False)
    result = SmartFillerService.fill_template(ResumeData(language=language, work=[{"company": "Example", "tasks": "Build systems"}]))
    prs = Presentation(result["pptx_path"])
    assert len(prs.slides) >= 1
    text = "\n".join(c.text for slide in prs.slides for shape in slide.shapes if shape.has_table for row in shape.table.rows for c in row.cells)
    assert "Build systems" in text
    assert "{{" not in text
