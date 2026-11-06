import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.resume import ProjectItem, ResumeData, WorkItem
from app.services.llm_service import LLMService
from app.services.summarization_service import SummarizationService


def test_recovers_dated_projects_nested_under_work_history():
    resume = ResumeData(
        language="CN",
        work=[WorkItem(
            company="示例科技公司",
            period="2020/01-现在",
            role="系统测试工程师",
            tasks="原始工作职责",
        )],
    )
    source = """工作经历
2020/01-现在
2023/06-现在：平台升级项目
编写系统测试方案
跟踪缺陷闭环
2021.02-2023.05：远程服务项目
执行接口与稳定性测试
维护自动化测试脚本
教育背景
2016.09-2020.06 示例大学
"""

    result = SummarizationService.recover_embedded_projects(resume, source)

    assert [project.name for project in result.project] == [
        "平台升级项目", "远程服务项目"
    ]
    assert all(project.company == "示例科技公司" for project in result.project)
    assert all(project.role == "系统测试工程师" for project in result.project)
    assert len(SummarizationService._task_items(result.project[0].tasks)) == 2
    assert "教育背景" not in result.project[-1].tasks


def test_employer_date_heading_is_not_treated_as_project():
    resume = ResumeData(
        work=[WorkItem(company="Example Ltd", period="2020.01-Present", role="Tester")]
    )
    source = """Work Experience
2020.01-Present Example Ltd
Migration Program 2022.03-2023.08
Validated service integration
Education
Example University
"""

    result = SummarizationService.recover_embedded_projects(resume, source)

    assert len(result.project) == 1
    assert result.project[0].name == "Migration Program"


def test_present_periods_overlap():
    work = SummarizationService._parse_period_range("2020/01-现在")
    project = SummarizationService._parse_period_range("2023.06-Present")

    assert SummarizationService._periods_overlap(work, project)


def test_existing_project_is_not_duplicated_by_date_format():
    resume = ResumeData(
        work=[WorkItem(company="Example", period="2020.01-Present", role="Tester")],
        project=[ProjectItem(
            name="Migration Program",
            period="2022.03 - 2023.08",
            tasks="Validated service integration",
        )],
    )
    source = """Work Experience
Migration Program 2022/03-2023/08
Validated service integration
Education
Example University
"""

    result = SummarizationService.recover_embedded_projects(resume, source)

    assert len(result.project) == 1


def test_work_overview_is_short_and_does_not_repeat_project_names():
    original = LLMService.call_llm

    async def fake_call(*args, **kwargs):
        return "统筹跨项目测试计划与交付；协调缺陷跟踪和质量闭环"

    LLMService.call_llm = staticmethod(fake_call)
    try:
        work = WorkItem(company="Example", period="2020.01-Present", role="Tester")
        projects = [ProjectItem(
            name="Migration Program",
            period="2022.03-2023.08",
            tasks="执行接口测试；维护自动化脚本",
        )]
        result = asyncio.run(
            SummarizationService.summarize_work_overview(work, projects, "CN")
        )
        items = SummarizationService._task_items(result.tasks)
        assert len(items) == 2
        assert "Migration Program" not in result.tasks
    finally:
        LLMService.call_llm = original


def test_work_identity_is_kept_when_all_details_are_nested_in_projects():
    resume = ResumeData(
        work=[WorkItem(
            company="Example",
            period="2020.01-Present",
            role="Tester",
            tasks=None,
        )],
        project=[ProjectItem(
            company="Example",
            period="2022.03-2023.08",
            name="Migration Program",
            role="Tester",
            tasks="Validated service integration",
        )],
    )

    result = SummarizationService._organize_experience_modules(resume)

    assert len(result.work) == 1
    assert result.work[0].company == "Example"


def test_project_summary_never_drops_responsibilities():
    original = SummarizationService.summarize_text

    async def incomplete_summary(*args, **kwargs):
        return "仅保留一项职责"

    SummarizationService.summarize_text = staticmethod(incomplete_summary)
    try:
        project = ProjectItem(tasks="第一项职责；第二项职责；第三项职责")
        result = asyncio.run(
            SummarizationService.summarize_project_item(project, "CN")
        )
        assert len(SummarizationService._task_items(result.tasks)) == 3
    finally:
        SummarizationService.summarize_text = original


def test_project_recovery_stops_at_language_and_software_section():
    resume = ResumeData(
        work=[WorkItem(
            company="Printfleet Inc.",
            period="2015.03 - 2017.07",
            role="Product Manager",
        )]
    )
    source = """PROJECT EXPERIENCE
Project Name: DCA & PFO & QuickAccessKey
Drove product iteration for DCA and PFO
LANGUAGE AND SOFTWARE CAPABILITIES
English (IELTS 8, GMAT 630, Business English)
Agile Scrum, Axure, Xmind, Office, Visio (Proficient)
EDUCATION / TRAINING
Example University
"""

    result = SummarizationService.recover_embedded_projects(resume, source)

    assert len(result.project) == 1
    assert result.project[0].tasks == "Drove product iteration for DCA and PFO"


def test_sanitize_removes_skill_section_leaked_into_project_tasks():
    resume = ResumeData(
        language="EN",
        project=[ProjectItem(
            name="DCA & PFO & QuickAccessKey",
            tasks=(
                "Drove product iteration for DCA and PFO;\n"
                "LANGUAGE AND SOFTWARE CAPABILITIES;\n"
                "English (IELTS 8, GMAT 630, Business English);\n"
                "Agile Scrum, Axure, Xmind, Office, Visio (Proficient)"
            ),
        )],
    )

    result = SummarizationService.sanitize_experience_data(resume)

    assert result.project[0].tasks == "Drove product iteration for DCA and PFO"
