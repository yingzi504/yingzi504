import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from app.schemas.resume import ResumeData
from app.services.pipeline_service import PipelineService
from app.services import pipeline_service as pipeline


@pytest.mark.parametrize('source', ['', 'Gender: female\nSex: male'])
def test_pause_before_anonymization_and_reuse_parse(monkeypatch, source):
    parser = AsyncMock(return_value={'text_content': source})
    extractor = AsyncMock(return_value=ResumeData(name='Alex', gender='male'))
    monkeypatch.setattr(pipeline.ParserService, 'parse_file', parser)
    monkeypatch.setattr(pipeline.ExtractorService, 'extract_structure', extractor)
    monkeypatch.setattr(PipelineService, '_find_uploaded_file', lambda _: 'fixture.pdf')
    for method in ('recover_work_history', 'recover_embedded_projects'):
        monkeypatch.setattr(pipeline.SummarizationService, method, lambda data, text: data)
    # Stop after reaching anonymization: this test deliberately isolates the gate.
    anonymize = Mock(side_effect=RuntimeError('test stop after confirmation'))
    monkeypatch.setattr(pipeline.AnonymizerService, 'anonymize_resume', anonymize)
    task_id = PipelineService.create_task(file_id='gender-gate')
    task = PipelineService.get_task(task_id)
    asyncio.run(PipelineService.run_pipeline(task_id))
    assert task.status == 'awaiting_input'
    assert task.to_status_dict()['required_input']['field'] == 'gender'
    anonymize.assert_not_called()
    task.gender_confirmation.confirm('female')
    asyncio.run(PipelineService.run_pipeline(task_id))
    parser.assert_awaited_once()
    extractor.assert_awaited_once()
    assert anonymize.call_args.args[0].gender == 'female'
    assert task.error_message == 'test stop after confirmation'
