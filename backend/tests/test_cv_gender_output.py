import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pptx import Presentation

from app.api.process import router
from app.schemas.resume import ResumeData
from app.services.pipeline_service import PipelineService
from app.services import pipeline_service as pipeline
from app.services.pdf_converter import PdfConverterService


@pytest.mark.parametrize('orientation', ['vertical', 'horizontal'])
@pytest.mark.parametrize('language', ['CN', 'EN'])
@pytest.mark.parametrize('gender', ['male', 'female'])
@pytest.mark.parametrize('source_known', [True, False])
def test_gender_api_and_generated_file(monkeypatch, tmp_path, language, gender, source_known, orientation):
    # Only source parsing/extraction are mocked. Translation of honorifics,
    # anonymization, template filling and filename generation run normally.
    source = f'Gender: {gender}' if source_known else 'Software engineer'
    parser = AsyncMock(return_value={'text_content': source})
    extractor = AsyncMock(return_value=ResumeData(name='王伟', gender='male', language='CN'))
    monkeypatch.setattr(pipeline.ParserService, 'parse_file', parser)
    monkeypatch.setattr(pipeline.ExtractorService, 'extract_structure', extractor)
    monkeypatch.setattr(PipelineService, '_find_uploaded_file', lambda _: 'fixture.pdf')
    monkeypatch.setattr(pipeline.SmartFillerService, 'OUTPUT_DIR', str(tmp_path))
    monkeypatch.setattr(PdfConverterService, 'is_available', lambda: False)
    task_id = PipelineService.create_task(file_id='gender-output', target_language=language, template_type=orientation)
    task = PipelineService.get_task(task_id)
    asyncio.run(PipelineService.run_pipeline(task_id))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    if not source_known:
        assert task.status == 'awaiting_input', task.error_message
        assert not list(tmp_path.glob('*.pptx'))
        assert client.post(f'/process/{task_id}/gender', json={'gender': 'invalid'}).status_code == 422
        starter = Mock()
        monkeypatch.setattr(PipelineService, 'start_pipeline', starter)
        response = client.post(f'/process/{task_id}/gender', json={'gender': gender})
        assert response.status_code == 200
        starter.assert_called_once_with(task_id)
        assert client.post(f'/process/{task_id}/gender', json={'gender': gender}).status_code == 409
        asyncio.run(PipelineService.run_pipeline(task_id))
    assert task.status == 'completed', task.error_message
    parser.assert_awaited_once()
    extractor.assert_awaited_once()
    assert task.resume_data['gender'] == gender
    title = 'Ms.' if gender == 'female' else 'Mr.'
    assert title in task.output_filename
    assert Path(task.output_path).is_file()
    prs = Presentation(task.output_path)
    text = '\n'.join(
        shape.text if shape.has_text_frame else
        '\n'.join(cell.text for row in shape.table.rows for cell in row.cells) if shape.has_table else ''
        for slide in prs.slides for shape in slide.shapes
    )
    expected = ('王女士' if gender == 'female' else '王先生') if language == 'CN' else title
    assert expected in text
    assert expected in task.resume_data['name']
    assert client.post(f'/process/{task_id}/gender', json={'gender': gender}).status_code == 409


def test_gender_api_missing_task():
    app = FastAPI()
    app.include_router(router)
    assert TestClient(app).post('/process/missing/gender', json={'gender': 'female'}).status_code == 404
