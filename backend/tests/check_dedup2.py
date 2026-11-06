"""Diagnose task dedup - check paragraph.text and tracking"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging, warnings
logging.basicConfig(level=logging.CRITICAL)
warnings.filterwarnings('ignore')

# Direct output to a file to avoid emoji encoding issues
report_path = os.path.join(os.environ.get('TEMP', '.'), 'dedup_debug.txt')
report = open(report_path, 'w', encoding='utf-8')

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

# Redirect stdout temporarily to suppress debug prints
import io
old_stdout = sys.stdout
sys.stdout = io.StringIO()

result = SmartFillerService.fill_template(r, TemplateType.NEW_CN, generate_pdf=False)

sys.stdout = old_stdout

prs = Presentation(result['pptx_path'])

for si, slide in enumerate(prs.slides):
    report.write(f'\n=== Slide {si+1} ===\n')
    for shape in slide.shapes:
        if shape.has_table:
            t = shape.table
            report.write(f'  表格 {len(t.rows)}行 x {len(t.columns)}列\n')
            for ri, row in enumerate(t.rows):
                cells = []
                for ci, cell in enumerate(row.cells):
                    txt = cell.text.strip()[:120].replace('\n', ' | ')
                    cells.append(txt)
                report.write(f'    Row {ri}: {cells}\n')
                
                # For work rows, dump paragraph details of cell 1
                if si == 0 and ri < 5 and len(row.cells) > 1:
                    c1 = row.cells[1]
                    paras = list(c1.text_frame.paragraphs)
                    report.write(f'    Cell 1 段落数: {len(paras)}\n')
                    for pi, p in enumerate(paras):
                        t = p.text[:60]
                        has_tasks = 'Task' in t
                        report.write(f'      Para {pi}: [{t}] tasks={has_tasks}\n')

report.close()
print(f'Report written to {report_path}')
print(open(report_path, encoding='utf-8').read())
