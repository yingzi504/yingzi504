from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote
import pytest
from pptx import Presentation
from app.core.cv_rules import cv_download_filename
from app.services.smart_filler_service import SmartFillerService
from app.services.pdf_converter import PdfConverterService
from app.services.pipeline_service import PipelineService
from app.services import access_service as service
from app.models.access import Resource
from test_access_control import context, signed_in


@pytest.mark.parametrize('extension', ['pptx', 'pdf'])
def test_remove_only_generated_suffix(extension):
    clean = f'IAV_Ms. Jiang_resume_Resume_CN_20260929.{extension}'
    stored = clean.replace(f'.{extension}', f'_b21a4e7cdfb2.{extension}')
    assert cv_download_filename(stored) == clean
    assert cv_download_filename(clean) == clean
    unrelated = f'JD_20260929_b21a4e7cdfb2.{extension}'
    assert cv_download_filename(unrelated) == unrelated


def test_clean_names_keep_storage_unique_and_pdf_detection(monkeypatch, tmp_path):
    monkeypatch.setattr(SmartFillerService, 'OUTPUT_DIR', str(tmp_path))
    monkeypatch.setattr(PdfConverterService, 'is_available', lambda: False)
    data = {'anonymized_name': 'Ms. Jiang', 'job_position_en': 'Engineer'}
    first = SmartFillerService._save_output_file(Presentation(), data, 'test')
    second = SmartFillerService._save_output_file(Presentation(), data, 'test')
    assert first['filename'] == second['filename']
    assert first['pptx_path'] != second['pptx_path']
    assert all(Path(result['pptx_path']).is_file() for result in [first, second])
    assert cv_download_filename(Path(first['pptx_path']).name) == first['filename']
    tid = PipelineService.create_task(file_id='name-test')
    task = PipelineService.get_task(tid)
    task.output_path = first['pptx_path']
    task.output_filename = first['filename']
    Path(first['pptx_path']).with_suffix('.pdf').write_bytes(b'PDF fixture')
    assert task.to_result_dict()['pdf_available'] is True
    task.status, task.current_step, task.progress = 'processing', 'LLM structured extraction', 40
    assert '%' not in task.to_status_dict()['message']
    assert task.to_status_dict()['progress'] == 40


def test_archive_and_legacy_downloads_have_clean_names(context):
    sessions, tmp = context
    admin = signed_in('admin@company.test')
    stored_name = 'IAV_Ms. Jiang_resume_Resume_CN_20260929_b21a4e7cdfb2.pptx'
    clean_name = cv_download_filename(stored_name)
    output = tmp / 'output'; output.mkdir()
    source = output / stored_name; source.write_bytes(b'PPTX fixture')
    service.import_legacy_outputs()
    legacy = admin.get('/api/v1/records').json()['data'][0]
    assert legacy['files'][0]['name'] == clean_name
    response = admin.get(f"/api/v1/records/{legacy['id']}/download?format=pptx")
    assert clean_name in unquote(response.headers['content-disposition'])
    with sessions() as db:
        db.add(Resource(id='cv-name-test', owner_id=1, kind='cv', name='source.docx'))
        db.commit()
    task = SimpleNamespace(task_id='cv-name-test', status='completed', output_path=str(source),
                           to_status_dict=lambda:{'status':'completed'})
    service.persist_task(task, 'cv')
    assert (output / 'archive' / 'cv-name-test' / clean_name).is_file()
    response = admin.get('/api/v1/records/cv-name-test/download?format=pptx')
    assert response.content == b'PPTX fixture'
    assert clean_name in unquote(response.headers['content-disposition'])
