import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Suppress all debug output from SmartFillerService
import logging
logging.getLogger().setLevel(logging.ERROR)

# Redirect stdout to suppress prints
import io
old_stdout = sys.stdout
sys.stdout = io.StringIO()

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.smart_filler_service import SmartFillerService
from app.services.template_config import TemplateType
from pptx import Presentation

r = ResumeData(
    name='Mr. Zhang', anonymized_name='Mr. Zhang', phone='13800138000',
    email='z@x.com', location='BJ', position='SE', technical_area='AI',
    total_exp='5y', summary='dev', tech_skills='Python', lang_skills='Eng',
    lang_skills_level='Fluent', training_exp='ML',
    education=[EducationItem(period='2015-2019', school='TU', degree='B', major='CS')],
    work=[WorkItem(company=f'Company {chr(65+i)}', period=f'202{i}', role=f'Engineer {i}', tasks=f'Task {i}') for i in range(5)],
    project=[ProjectItem(company=f'C{chr(65+i)}', period=f'202{i}', name=f'Project {i}', role=f'Role {i}', tasks=f'PTask {i}') for i in range(5)]
)

sys.stdout = old_stdout
result = SmartFillerService.fill_template(r, TemplateType.NEW_CN, generate_pdf=False)
prs = Presentation(result['pptx_path'])

print(f'总页数: {len(prs.slides)}')
for si, slide in enumerate(prs.slides):
    print(f'\n=== Slide {si+1} ===')
    for shape in slide.shapes:
        if shape.has_table:
            t = shape.table
            print(f'  表格 {len(t.rows)}行 x {len(t.columns)}列')
            for ri, row in enumerate(t.rows):
                cells = []
                for ci, cell in enumerate(row.cells):
                    txt = cell.text.strip()[:100].replace('\n', ' | ')
                    cells.append(txt)
                print(f'    Row {ri}: {cells}')
