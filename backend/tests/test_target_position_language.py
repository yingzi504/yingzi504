from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.process import _detect_job_position_language
from app.services.pipeline_service import PipelineService


def test_target_position_language_validation():
    assert _detect_job_position_language('高级测试工程师') == 'CN'
    assert _detect_job_position_language('Test Engineer') == 'EN'
    assert _detect_job_position_language('') is None

    assert PipelineService.validate_target_position_language('高级测试工程师', 'CN') is None
    assert PipelineService.validate_target_position_language('Test Engineer', 'EN') is None
    assert PipelineService.validate_target_position_language('高级测试工程师', 'EN')
    assert PipelineService.validate_target_position_language('Test Engineer', 'CN')
