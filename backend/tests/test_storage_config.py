from pathlib import Path

from app.core.config import (
    BACKEND_DIR,
    Settings,
    ensure_storage_directories,
    settings,
)


def test_relative_storage_paths_are_resolved_from_backend_directory():
    config = Settings(
        debug=True,
        upload_dir="../runtime/uploads",
        output_dir="../runtime/output",
        _env_file=None,
    )

    assert config.upload_path == (BACKEND_DIR.parent / "runtime" / "uploads").resolve()
    assert config.output_path == (BACKEND_DIR.parent / "runtime" / "output").resolve()


def test_storage_directories_are_created_and_writable(tmp_path):
    config = Settings(
        debug=True,
        upload_dir=str(tmp_path / "uploads"),
        output_dir=str(tmp_path / "output"),
        _env_file=None,
    )

    ensure_storage_directories(config)

    assert config.upload_path.is_dir()
    assert config.output_path.is_dir()
    assert not list(config.upload_path.glob(".write-probe-*"))
    assert not list(config.output_path.glob(".write-probe-*"))


def test_upload_pipeline_and_fillers_share_configured_paths():
    from app.api.resume import OUTPUT_DIR as API_OUTPUT_DIR
    from app.api.resume import UPLOAD_DIR as API_UPLOAD_DIR
    from app.services.advanced_smart_filler import AdvancedSmartFiller
    from app.services.filler_service import FillerService
    from app.services.pipeline_service import UPLOAD_DIR as PIPELINE_UPLOAD_DIR
    from app.services.smart_filler_service import SmartFillerService

    assert Path(API_UPLOAD_DIR) == settings.upload_path
    assert Path(PIPELINE_UPLOAD_DIR) == settings.upload_path
    assert Path(API_OUTPUT_DIR) == settings.output_path
    assert Path(FillerService.OUTPUT_DIR) == settings.output_path
    assert Path(AdvancedSmartFiller.OUTPUT_DIR) == settings.output_path
    assert Path(SmartFillerService.OUTPUT_DIR) == settings.output_path
