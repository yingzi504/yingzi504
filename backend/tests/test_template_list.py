from pathlib import Path

from app.services.smart_filler_service import SmartFillerService
from app.services.template_config import TEMPLATE_CONFIG, TemplateType
from app.services.template_service import TemplateService


def test_template_directory_is_shared_by_template_services():
    smart_filler_dir = Path(SmartFillerService.TEMPLATES_DIR).resolve()

    assert smart_filler_dir.is_dir()
    assert TemplateService.TEMPLATES_DIR.resolve() == smart_filler_dir


def test_bundled_template_metadata_is_complete():
    assert set(TEMPLATE_CONFIG) == {item.value for item in TemplateType}

    for metadata in TEMPLATE_CONFIG.values():
        assert metadata["orientation"] in {"portrait", "landscape"}
        assert metadata["language"] in {"CN", "EN"}
        assert metadata["file"].endswith(".pptx")


def test_every_bundled_template_file_exists():
    for template_id, metadata in TEMPLATE_CONFIG.items():
        template_path = Path(SmartFillerService.get_template_path(template_id))
        assert template_path.name == metadata["file"]
        assert template_path.is_file()
