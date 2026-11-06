import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pptx import Presentation
from pptx.util import Pt

from app.schemas.resume import ProjectItem, ResumeData
from app.services.extractor_service import ExtractorService
from app.services.smart_filler_service import SmartFillerService
from app.services.summarization_service import SummarizationService


def test_wang_responsibility_blocks_are_assigned_in_source_order():
    data = {
        'work': [
            {'company': 'Capgemini Consulting (Shanghai) Co.', 'tasks': ''},
            {
                'company': 'Anhui Jianghuai Automobile Technology Center',
                'tasks': 'incorrect merged tasks',
            },
        ]
    }
    raw = '''Responsibilities:
Responsible for the integration and commissioning of test benches.
• Test bench hardware integration: inspection and installation;
• Test bench software integration: version upgrades and compatibility testing.
Performance:
Completed three test rigs.
Harvest:
Learned the integration workflow.
Responsibilities：
Responsible for inverse analysis of CAN bus signal data.
• Confirm target vehicles and generate the signal list;
Work experience
• Verify the CAN bus signal database in real vehicles.
Performance:
Parsed more than 30 vehicle models.
'''

    ExtractorService._recover_ordered_responsibility_blocks(raw, data)

    assert 'integration and commissioning' in data['work'][0]['tasks']
    assert 'CAN bus signal' not in data['work'][0]['tasks']
    assert data['work'][0]['tasks'].count(';\n') == 2
    assert 'inverse analysis of CAN bus signal' in data['work'][1]['tasks']
    assert 'integration and commissioning' not in data['work'][1]['tasks']
    assert 'incorrect merged tasks' not in data['work'][1]['tasks']
    assert data['work'][1]['tasks'].count(';\n') == 2


def test_responsibility_recovery_skips_ambiguous_extra_blocks():
    data = {
        'work': [
            {'company': 'Company A', 'tasks': ''},
            {'company': 'Company B', 'tasks': 'keep existing tasks'},
        ]
    }
    raw = '''Responsibilities:
First work responsibility.
Performance:
Result A.
Responsibilities:
Second work responsibility.
Performance:
Result B.
Responsibilities:
Unrelated project responsibility.
Performance:
Result C.
'''

    ExtractorService._recover_ordered_responsibility_blocks(raw, data)

    assert data['work'][0]['tasks'] == ''
    assert data['work'][1]['tasks'] == 'keep existing tasks'


def test_project_company_uses_existing_template_json_field():
    resume = ResumeData(
        name='Mr. Zhao',
        language='EN',
        project=[ProjectItem(
            company='Capgemini Engineering',
            period='2022.11 - Present',
            name='TAVASCAN',
            role='Test Engineer',
            tasks='Reviewed requirements',
        )],
    )
    prs = Presentation(SmartFillerService.get_template_path('new_en'))
    modules = SmartFillerService.collect_all_modules(prs)
    data_map = SmartFillerService._prepare_module_data(resume.model_dump(), modules)
    SmartFillerService._smart_pagination_fill(
        prs,
        modules,
        data_map,
        SmartFillerService.build_replacements(resume.model_dump()),
    )

    project_text = '\n'.join(
        cell.text
        for slide in prs.slides
        for shape in slide.shapes
        if shape.has_table
        for row in shape.table.rows
        for cell in row.cells
        if 'TAVASCAN' in cell.text
    )
    assert 'Capgemini Engineering, TAVASCAN' in project_text


def test_row_height_estimate_matches_single_spaced_output():
    height = SmartFillerService._estimate_text_height(
        'One line of work experience text',
        12,
        Pt(400),
        line_spacing_factor=1.0,
    )
    assert height.pt == 12


def test_sanitize_experience_data_removes_numeric_projects_and_bad_months():
    resume = ResumeData(
        work=[{"company": "Company", "period": "2019.09 - 2020.00"}],
        project=[
            {"name": "2", "period": "2019.09 - 2020.00", "tasks": "artefact"},
            {"name": "ADAS Platform", "period": "2021.03 - Present", "tasks": "valid"},
        ],
    )

    cleaned = SummarizationService.sanitize_experience_data(resume)

    assert len(cleaned.project) == 1
    assert cleaned.project[0].name == "ADAS Platform"
    assert cleaned.project[0].period == "2021.03 - Present"
    assert cleaned.work[0].period is None


def test_smart_pagination_forces_progress_for_oversized_item(monkeypatch):
    prs = Presentation(SmartFillerService.get_template_path('new_en'))
    modules = SmartFillerService.collect_all_modules(prs)
    data_map = {name: [] for name in ('work', 'project', 'education', 'skill')}
    data_map['project'] = [ProjectItem(name='Oversized', tasks='x' * 10000)]

    monkeypatch.setattr(
        SmartFillerService,
        'calculate_pagination_for_module',
        staticmethod(lambda *args, **kwargs: (0, 0)),
    )
    SmartFillerService._smart_pagination_fill(
        prs,
        modules,
        data_map,
        SmartFillerService.build_replacements(ResumeData(language='EN').model_dump()),
    )

    assert len(prs.slides) < 4
