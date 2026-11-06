"""Names must reach the LLM and participate in the normal repair/audit path."""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.resume import ResumeData
from app.services.llm_service import LLMService
from app.services.translator_service import TranslatorService as T


@pytest.mark.parametrize("source,context,translated", [
    ("Audi China", "company", "奥迪中国"),
    ("Capgemini China", "company", "凯捷中国"),
    ("Tencent Inc.", "company", "腾讯"),
    ("Asterix", "company", "阿斯特里克斯"),
    ("Queen’s University, Smith School of Business", "school", "女王大学史密斯商学院"),
    ("University of Waterloo", "school", "滑铁卢大学"),
    ("Master Degree", "degree", "硕士"),
    ("Bachelor", "degree", "学士"),
    ("Red Plum app-retention, backend management", "project", "红梅应用用户留存与后台管理"),
])
def test_names_are_translated_and_unchanged_output_is_repaired(source, context, translated):
    model = AsyncMock(side_effect=[source, translated])
    with patch.object(LLMService, "call_llm", new=model), patch.object(T, "_wait_for_repair", new=AsyncMock()):
        result = asyncio.run(T.translate_text(source, "CN", "CN", context=context))
    assert result == translated
    assert model.await_count == 2
    assert source in model.await_args.kwargs["prompt"]
    assert "source_language_residue" in model.await_args.kwargs["prompt"]
    assert "音译或意译" in model.await_args.kwargs["system_prompt"]


def test_resume_names_are_localized_without_overwriting_source():
    source = ResumeData(
        language="CN",
        work=[{"company": "Audi China"}, {"company": "Tencent Inc."}],
        education=[{"school": "University of Waterloo", "degree": "Bachelor"}],
        project=[{"company": "Capgemini China", "name": "Red Plum backend management"}],
    )
    mapping = {
        "Audi China": "奥迪中国", "Tencent Inc.": "腾讯",
        "University of Waterloo": "滑铁卢大学", "Bachelor": "学士",
        "Capgemini China": "凯捷中国", "Red Plum backend management": "红梅后台管理",
    }
    async def respond(*, prompt, **kwargs):
        for original, localized in mapping.items():
            if original in prompt:
                return localized
        pytest.fail("Unexpected translation request")

    assert set(T.audit_translation(source, "CN")) == {
        "work[0].company", "work[1].company", "education[0].school",
        "education[0].degree", "project[0].company", "project[0].name",
    }
    with patch.object(LLMService, "call_llm", new=AsyncMock(side_effect=respond)) as model:
        result = asyncio.run(T.translate_resume(source, "CN"))
    assert model.await_count == 6
    assert result.work[0].company == "奥迪中国"
    assert result.work[1].company == "腾讯"
    assert result.education[0].school == "滑铁卢大学"
    assert result.education[0].degree == "学士"
    assert result.project[0].company == "凯捷中国"
    assert result.project[0].name == "红梅后台管理"
    assert T.audit_translation(result, "CN") == []
    assert source.work[0].company == "Audi China"


def test_name_policy_preserves_project_identifiers_but_not_institutions():
    assert not T._has_language_residue("DCA & PFO & QuickAccessKey", "CN", "project_name")
    assert not T._has_language_residue("QuickAccessKey 后台管理", "CN", "project_name")
    assert T._has_language_residue("Red Plum", "CN", "project_name")
    assert T._has_language_residue("奥迪 China", "CN", "proper_noun")
    assert T._has_language_residue("MBA", "CN", "academic")
    assert not T._has_language_residue("University of Waterloo", "EN", "proper_noun")
    assert T._has_language_residue("滑铁卢大学", "EN", "proper_noun")


def test_unresolved_name_remains_visible_to_final_audit():
    model = AsyncMock(return_value="Audi China")
    with patch.object(LLMService, "call_llm", new=model), patch.object(T, "_wait_for_repair", new=AsyncMock()):
        result = asyncio.run(T.translate_resume(ResumeData(work=[{"company": "Audi China"}]), "CN"))
    assert model.await_count == T.MAX_TRANSLATION_ATTEMPTS
    assert result.work[0].company == "Audi China"
    assert T.audit_translation(result, "CN") == ["work[0].company"]
