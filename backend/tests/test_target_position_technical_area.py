import asyncio
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.pipeline_service import PipelineService
from app.services.smart_filler_service import SmartFillerService
from app.services.translator_service import TranslatorService


async def _run_checks():
    assert await PipelineService._resolve_target_technical_area("", "CN") == ""
    assert await PipelineService._resolve_target_technical_area("整车测试工程师", "CN") == "整车测试工程师"
    assert await PipelineService._resolve_target_technical_area("Vehicle Test Engineer", "EN") == "Vehicle Test Engineer"

    async def fake_translate(
        text,
        source_lang,
        target_lang,
        context=None,
        field_path=None,
    ):
        translations = {
            ("Vehicle Test Engineer", "CN"): "整车测试工程师",
            ("整车测试工程师", "EN"): "Vehicle Test Engineer",
        }
        return translations.get((text, target_lang), text)

    with patch.object(
        TranslatorService, "translate_text", new=AsyncMock(side_effect=fake_translate)
    ):
        assert await PipelineService._resolve_target_technical_area(
            "Vehicle Test Engineer", "CN"
        ) == "整车测试工程师"
        assert await PipelineService._resolve_target_technical_area(
            "整车测试工程师", "EN"
        ) == "Vehicle Test Engineer"

    assert SmartFillerService.build_replacements({"technical_area": "整车测试工程师"})[
        "{{technical_area}}"
    ] == "整车测试工程师"
    assert SmartFillerService.build_replacements({"technical_area": ""})[
        "{{technical_area}}"
    ] == ""


if __name__ == "__main__":
    asyncio.run(_run_checks())
    print("Target position technical-area checks passed")
