import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pptx import Presentation

from app.schemas.resume import ResumeData, WorkItem, ProjectItem
from app.services.anonymizer_service import AnonymizerService
from app.services.extractor_service import ExtractorService
from app.services.llm_service import LLMService
from app.services.smart_filler_service import SmartFillerService
from app.services.translator_service import TranslatorService
from app.services.summarization_service import SummarizationService


def test_name_recovery_uses_filename_and_full_text():
    assert ExtractorService._resolve_name(
        "F", "Fang Peng\nProfessional skills", "方鹏resume.pdf"
    ) == "方鹏"
    assert ExtractorService._resolve_name(
        "Candidate", "1\nKan Jian\n2012.09~2016.06", "HIL测试工程师岗位简历_英文_阚健20230509.pdf"
    ) == "阚健"
    assert ExtractorService._resolve_name(
        "Candidate", "1\n阚健\n2012.09~2016.06", "智能驾驶工程师岗位简历_20230505.pdf"
    ) == "阚健"


def test_periods_are_zero_padded_and_uniform():
    assert TranslatorService.normalize_period("March 2022 — present", "EN") == "2022.03 - Present"
    assert TranslatorService.normalize_period("September 2020 - March2022", "CN") == "2020.09 - 2022.03"
    assert TranslatorService.normalize_period("September 2020 — March 2022", "CN") == "2020.09 - 2022.03"
    assert TranslatorService.normalize_period("2023.3~2023.05", "CN") == "2023.03 - 2023.05"
    assert TranslatorService.normalize_period("2021年9月至2022年3月", "CN") == "2021.09 - 2022.03"
    assert TranslatorService.normalize_period("2019 - 2022", "CN") == "2019.01 - 2022.12"


def test_project_period_is_recovered_when_title_precedes_date():
    projects = [{"name": "智能座舱项目", "period": ""}]
    ExtractorService._enrich_project_periods(
        projects, "项目经历\n智能座舱项目\n2018.12-2023.04\n"
    )
    assert projects[0]["period"] == "2018.12 - 2023.04"


def test_skills_fallback_extracts_tools_from_experience():
    data = {"work": [], "project": []}
    ExtractorService._infer_skills(
        data, "Built a test bench and used CANoe, Python, Linux and ADB for infotainment testing."
    )
    assert data["tech_skills"] == "CANoe; ADB"


def test_skills_keep_only_source_backed_named_software():
    data = {
        "tech_skills": "CANoe; Python; Agile; CAN; Jira; InventedTool",
        "work": [],
        "project": [],
    }
    ExtractorService._infer_skills(
        data,
        "Used CANoe and Jira for CAN testing in an Agile team; developed Python scripts.",
    )
    assert data["tech_skills"] == "CANoe; Jira"


def test_skills_remove_model_items_without_source_evidence():
    data = {"tech_skills": "CANoe software; Jira", "work": [], "project": []}
    ExtractorService._infer_skills(
        data, "Used CANoe software and created reports with Microsoft Office."
    )
    assert data["tech_skills"] == "CANoe; Microsoft Office"


def test_plain_office_word_is_not_treated_as_microsoft_office():
    data = {"tech_skills": "Office", "work": [], "project": []}
    ExtractorService._infer_skills(data, "Worked from the Shanghai office.")
    assert data["tech_skills"] is None


def test_kan_name_does_not_become_candidate():
    data = AnonymizerService.anonymize_resume(
        ResumeData(name="阚健", language="EN")
    )
    assert data.name == "Mr. Kan"
    assert data.anonymized_name_cn == "阚先生"
    assert data.model_dump()["anonymized_name_cn"] == "阚先生"


def test_onepager_grouped_placeholders_are_filled():
    resume = ResumeData(
        name="方先生",
        anonymized_name="方先生",
        language="CN",
        total_exp="3年",
        work=[WorkItem(period="2023.03 - 2023.05", role="测试工程师", company="公司")],
        project=[ProjectItem(period="2023.03 - 2023.05", role="测试工程师", company="公司", name="项目", tasks="完成测试")],
        tech_skills="CANoe",
    )
    prs = Presentation(SmartFillerService.get_template_path("onepager_cn"))
    SmartFillerService._fill_non_table_fields(
        prs, SmartFillerService.build_replacements(resume.model_dump())
    )
    leftovers = [
        shape.text
        for shape in SmartFillerService._iter_nested_shapes(prs.slides[0].shapes)
        if getattr(shape, "has_text_frame", False) and "{{" in shape.text
    ]
    assert leftovers == []


def test_translation_retries_when_mixed_language_remains():
    import asyncio

    original = LLMService.call_llm
    responses = iter([
        "海拉 Research and Development Center",
        "海拉南京研发中心",
    ])

    async def fake_call_llm(*args, **kwargs):
        return next(responses)

    LLMService.call_llm = staticmethod(fake_call_llm)
    try:
        result = asyncio.run(
            TranslatorService.translate_text(
                "Acme Research and Development Center",
                "EN",
                "CN",
                context="公司名称",
            )
        )
        assert result == "海拉南京研发中心"
    finally:
        LLMService.call_llm = original


def test_translation_infers_source_language_from_fields():
    resume = ResumeData(
        language="CN",
        work=[WorkItem(company="Acme Research Center", role="Senior Test Engineer")],
    )
    assert TranslatorService._infer_resume_language(resume) == "EN"
    assert not hasattr(TranslatorService, "_CN_TERM_REPLACEMENTS")
    assert TranslatorService.normalize_period("2023.3~2023.05", "CN") == "2023.03 - 2023.05"


def test_translation_cleans_mixed_prose_but_preserves_official_company_name():
    import asyncio

    original = LLMService.call_llm

    async def fake_call_llm(*args, **kwargs):
        return "已翻译"

    LLMService.call_llm = staticmethod(fake_call_llm)
    try:
        result = asyncio.run(
            TranslatorService.translate_resume(
                ResumeData(
                    language="CN",
                    work=[WorkItem(
                        company="Acme Research Center",
                        period="2023.3~2023.05",
                        role="Senior Test Engineer",
                        tasks="Coordinate with supplier and adjust test platform",
                    )],
                ),
                "CN",
            )
        )
        assert result.language == "CN"
        assert result.work[0].company == "Acme Research Center"
        assert result.work[0].role == "已翻译"
        assert result.work[0].tasks == "已翻译"
        assert result.work[0].period == "2023.03 - 2023.05"
    finally:
        LLMService.call_llm = original


def test_llm_json_retries_empty_response():
    import asyncio

    original = LLMService.call_llm
    responses = iter(["", '{"name": "Retry OK"}'])

    async def fake_call_llm(*args, **kwargs):
        return next(responses)

    LLMService.call_llm = staticmethod(fake_call_llm)
    try:
        result = asyncio.run(LLMService.call_llm_json(prompt="test", max_tokens=100))
        assert result["name"] == "Retry OK"
    finally:
        LLMService.call_llm = original


def test_llm_json_accepts_quoted_json_object():
    import asyncio

    original = LLMService.call_llm

    async def fake_call_llm(*args, **kwargs):
        return '"{\\"name\\": \\"Quoted OK\\"}"'

    LLMService.call_llm = staticmethod(fake_call_llm)
    try:
        result = asyncio.run(LLMService.call_llm_json(prompt="test", max_tokens=100))
        assert result["name"] == "Quoted OK"
    finally:
        LLMService.call_llm = original


def test_extractor_uses_local_fallback_after_llm_failure():
    import asyncio
    from fastapi import HTTPException

    original = LLMService.call_llm_json

    async def failing_call(*args, **kwargs):
        raise HTTPException(status_code=500, detail="empty response")

    LLMService.call_llm_json = staticmethod(failing_call)
    try:
        result = asyncio.run(
            ExtractorService.extract_structure(
                "Fang Peng\nEmail: fang@example.com\nUsed CANoe and Python for testing.",
                "Fang Peng resume.pdf",
            )
        )
        assert result.name == "Fang Peng"
        assert result.email == "fang@example.com"
        assert "CANoe" in (result.tech_skills or "")
    finally:
        LLMService.call_llm_json = original


def test_task_summary_does_not_drop_items():
    import asyncio

    original = SummarizationService.summarize_text

    async def incomplete_summary(*args, **kwargs):
        return "仅保留第一条"

    SummarizationService.summarize_text = staticmethod(incomplete_summary)
    try:
        result = asyncio.run(SummarizationService.summarize_work_item(
            WorkItem(tasks="第一条职责；第二条职责；第三条职责"), "CN"
        ))
        assert len(SummarizationService._task_items(result.tasks)) == 3
    finally:
        SummarizationService.summarize_text = original


def test_task_translation_keeps_every_item():
    import asyncio

    original = TranslatorService.translate_text
    translated_sources = []

    async def fake_translate(text, *args, **kwargs):
        translated_sources.append(text)
        return f"translated item {len(translated_sources)}"

    TranslatorService.translate_text = staticmethod(fake_translate)
    try:
        result = asyncio.run(TranslatorService._translate_task_list(
            "第一条；第二条；第三条", "CN", "EN", "工作内容"
        ))
        assert len(TranslatorService._task_items(result)) == 3
        assert "translated item 3" in result
        assert translated_sources == ["第一条", "第二条", "第三条"]
    finally:
        TranslatorService.translate_text = original


def test_extractor_recovers_omitted_work_bullets_from_source_section():
    data = {
        "work": [{
            "company": "示例科技有限公司",
            "period": "2018.12 - 2023.04",
            "tasks": "",
        }]
    }
    raw = (
        "工作经历\n2018.12-2023.04 示例科技有限公司 项目经理\n"
        "工作描述：负责项目管理\n"
        "⚫ 第一项职责\n⚫ 第二项职责\n⚫ 第三项职责\n"
        "项目经历\n⚫ 项目职责"
    )
    ExtractorService._recover_missing_work_tasks(data, raw)
    assert len(ExtractorService._task_items(data["work"][0]["tasks"])) == 3


def test_extractor_pipeline_repairs_valid_but_incomplete_llm_json():
    import asyncio

    original = LLMService.call_llm_json
    raw = (
        "工作经历\n2020.01-2023.04 示例科技有限公司 测试经理\n"
        "⚫ 负责需求分析\n⚫ 负责测试计划\n⚫ 负责缺陷闭环\n"
        "教育经历\n2020-2023 示例大学"
    )

    async def incomplete_json(*args, **kwargs):
        return {
            "name": "测试人员",
            "language": "CN",
            "work": [{
                "company": "示例科技有限公司",
                "period": "2020.01 - 2023.04",
                "role": "测试经理",
                "tasks": "",
            }],
        }

    LLMService.call_llm_json = staticmethod(incomplete_json)
    try:
        result = asyncio.run(ExtractorService.extract_structure(raw, "示例测试人员.pdf"))
        assert len(ExtractorService._task_items(result.work[0].tasks)) == 3
    finally:
        LLMService.call_llm_json = original


def test_project_resume_keeps_work_identity_and_fills_project_metadata():
    resume = ResumeData(
        language="EN",
        work=[WorkItem(
            company="JunJiu",
            period="2020.09 - 2022.03",
            role="Infotainment Engineer",
            tasks="",
        )],
        project=[ProjectItem(
            period="2021.01 - 2021.08",
            tasks="Tested the infotainment system",
        )],
    )
    organized = SummarizationService._organize_experience_modules(resume)
    assert len(organized.work) == 1
    assert organized.work[0].company == "JunJiu"
    assert organized.project[0].company == "JunJiu"
    assert organized.project[0].role == "Infotainment Engineer"


def test_work_only_resume_removes_empty_project_module():
    resume = ResumeData(
        language="CN",
        work=[WorkItem(
            company="示例公司",
            period="2020.01 - 2022.03",
            role="测试工程师",
            tasks="完成测试与缺陷闭环",
        )],
    )
    organized = SummarizationService._organize_experience_modules(resume)
    assert len(organized.work) == 1
    assert organized.project == []


def test_work_and_project_tasks_keep_overview_and_detail_separate():
    resume = ResumeData(
        language="EN",
        work=[WorkItem(
            company="A",
            period="2020.01 - 2022.03",
            tasks="Conducted regression tests; Coordinated release delivery",
        )],
        project=[ProjectItem(
            company="A",
            period="2021.01 - 2021.08",
            tasks="Conducted regression tests",
        )],
    )
    organized = SummarizationService._organize_experience_modules(resume)
    result = SummarizationService._deduplicate_work_tasks(
        organized.work, organized.project
    )
    assert result[0].tasks == "Coordinated release delivery"


def test_project_only_template_removes_work_title_and_table():
    from pptx import Presentation

    resume = ResumeData(
        name="Mr. Fang",
        language="EN",
        project=[ProjectItem(
            period="2021.01 - 2021.08",
            company="A",
            name="Project P",
            role="Tester",
            tasks="Tested the system",
        )],
    )
    prs = Presentation(SmartFillerService.get_template_path("new_en"))
    modules = SmartFillerService.collect_all_modules(prs)
    data_map = SmartFillerService._prepare_module_data(resume.model_dump(), modules)
    SmartFillerService._smart_pagination_fill(
        prs, modules, data_map,
        SmartFillerService.build_replacements(resume.model_dump()),
    )
    assert "work" not in [module.name for module in SmartFillerService.collect_all_modules(prs)]
    assert "project" in [module.name for module in SmartFillerService.collect_all_modules(prs)]


def test_extractor_clears_work_tasks_copied_from_project_only_source():
    import asyncio

    original = LLMService.call_llm_json
    raw = (
        "Work Experience\nExample Company\n"
        "Project experience\nProject A 2021.01-2021.08\n"
        "1. Test the infotainment system\n"
    )

    async def copied_work_json(*args, **kwargs):
        return {
            "name": "Example Candidate",
            "language": "EN",
            "work": [{
                "company": "Example Company",
                "period": "2021.01 - 2021.08",
                "role": "Tester",
                "tasks": "Test the infotainment system",
            }],
            "project": [{
                "period": "2021.01 - 2021.08",
                "name": "Project A",
                "tasks": "Test the infotainment system",
            }],
        }

    LLMService.call_llm_json = staticmethod(copied_work_json)
    try:
        result = asyncio.run(ExtractorService.extract_structure(raw, "example.pdf"))
        assert result.work[0].tasks == ""
    finally:
        LLMService.call_llm_json = original
