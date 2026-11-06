"""Behavioral regressions for iterative translation repair."""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.resume import transform_resume
from app.schemas.resume import ResumeData, TransformRequest
from app.services.llm_service import LLMService
from app.services.translator_service import TranslatorService as T


def test_cn_stops_at_limit_and_preserves_product_names():
    outputs = ["负责 product delivery，使用 PRD 与 Audi"] * 4
    outputs.append("负责产品交付，使用 PRD 与 Audi")
    model = AsyncMock(side_effect=outputs)
    with (
        patch.object(LLMService, "call_llm", new=model),
        patch.object(T, "_wait_for_repair", new=AsyncMock()),
    ):
        result = asyncio.run(T.translate_text(
            "Responsible for product delivery using PRD at Audi", "EN", "CN",
            field_path="summary",
        ))
    assert result == outputs[2]
    assert model.await_count == 3
    assert '本轮待翻译残留：["product", "delivery"]' in model.await_args.kwargs["prompt"]


def test_task_list_does_not_restart_repairs_and_keeps_order():
    counts = {}

    async def translate(text, *args, field_path=None, **kwargs):
        counts[field_path] = counts.get(field_path, 0) + 1
        if field_path == "work[0].tasks[1]" and counts[field_path] < 4:
            return "Partial 残留"
        return f"Completed {field_path}"

    with (
        patch.object(T, "translate_text", new=AsyncMock(side_effect=translate)),
        patch.object(T, "_wait_for_repair", new=AsyncMock()),
    ):
        result = asyncio.run(T._translate_task_list(
            "第一项；第二项；第三项", "CN", "EN", "work",
            field_path="work[0].tasks",
        ))
    assert counts == {"work[0].tasks[0]": 1, "work[0].tasks[1]": 1, "work[0].tasks[2]": 1}
    assert T._task_items(result) == ["Completed work[0].tasks[0]", "Partial 残留", "Completed work[0].tasks[2]"]


def test_persistent_residue_remains_pending_and_can_be_cancelled():
    async def scenario():
        waiting = asyncio.Event()
        never = asyncio.Event()

        async def pause(*args):
            waiting.set()
            await never.wait()

        with (
            patch.object(LLMService, "call_llm", new=AsyncMock(return_value="残留")),
            patch.object(T, "_wait_for_repair", new=AsyncMock(side_effect=pause)),
        ):
            task = asyncio.create_task(T.translate_text("职责", "CN", "EN"))
            await asyncio.wait_for(waiting.wait(), timeout=1)
            assert not task.done()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    asyncio.run(scenario())


def test_provider_error_stops_siblings_and_is_not_reported_as_quality_error():
    async def scenario():
        started = asyncio.Event()
        stopped = asyncio.Event()
        never = asyncio.Event()

        async def translate(text, *args, field_path=None, **kwargs):
            if field_path.endswith("[0]"):
                started.set()
                try:
                    await never.wait()
                finally:
                    stopped.set()
            await started.wait()
            raise HTTPException(503, "Provider unavailable")

        with patch.object(T, "translate_text", new=AsyncMock(side_effect=translate)):
            with pytest.raises(HTTPException) as error:
                await T._translate_task_list(
                    "第一项；第二项", "CN", "EN", "work", field_path="work[0].tasks"
                )
        assert error.value.status_code == 503
        assert stopped.is_set()

    asyncio.run(scenario())


def test_same_language_metadata_does_not_skip_residual_translation_in_transform():
    model = AsyncMock(side_effect=["Summary 仍有残留", "Clean summary"])
    request = TransformRequest(
        resume_data=ResumeData(language="EN", summary="Summary 中文残留"),
        target_language="EN", perform_anonymization=False,
    )
    with patch.object(LLMService, "call_llm", new=model):
        response = asyncio.run(transform_resume(request))
    assert response.success
    assert response.data.summary == "Clean summary"
    assert model.await_count == 2


def test_free_form_dates_do_not_trigger_unrepairable_format_loop():
    resume = ResumeData(language="EN", work=[{"period": "2023"}])
    with patch.object(LLMService, "call_llm", new=AsyncMock()) as model:
        result = asyncio.run(T.review_and_retranslate(resume, "EN"))
    assert result.work[0].period == "2023"
    model.assert_not_awaited()


@pytest.mark.parametrize("code", ["VX", "JV", "CN", "SE", "EG", "IT", "HR"])
def test_two_letter_department_codes_in_chinese_are_not_residue(code):
    text = f"与 {code} 部门沟通，确保按时交付"
    assert not T._has_language_residue(text, "CN")


@pytest.mark.parametrize("word", ["IN", "ON", "TO", "OF", "BY", "AS", "IS", "WE"])
def test_uppercase_english_words_are_not_exempted_as_department_codes(word):
    assert T._has_language_residue(f"负责产品 {word} 交付", "CN")


def test_repaired_department_codes_pass_task_and_final_review_without_loop():
    translations = {
        "Coordinate with the VX department": "与 VX 部门同步信息",
        "Resolve JV escalations": "处理 JV 升级问题",
        "Coordinate with Cariad CN and SE": "与 Cariad CN 和 SE 沟通，确保按时交付",
    }
    async def model(**kwargs):
        for source, translated in translations.items():
            if source in kwargs["prompt"]:
                return translated
        pytest.fail("Unexpected repeated translation")

    resume = ResumeData(language="EN", work=[{"tasks": ";\n".join(translations)}])
    with (
        patch.object(LLMService, "call_llm", new=AsyncMock(side_effect=model)) as llm,
        patch.object(T, "_wait_for_repair", new=AsyncMock()) as wait,
    ):
        result = asyncio.run(T.translate_resume(resume, "CN"))
    assert T._task_items(result.work[0].tasks) == list(translations.values())
    assert T.audit_translation(result, "CN") == []
    assert llm.await_count == 3
    wait.assert_not_awaited()


@pytest.mark.parametrize("outputs, expected", [
    (["Draft 残留"] * 3, "Draft 残留"),
    (["Draft 残留", "", ""], "Draft 残留"),
    (["", "", ""], "原文职责"),
])
def test_persistent_quality_failure_returns_nonempty_draft(outputs, expected):
    model = AsyncMock(side_effect=outputs)
    with patch.object(LLMService, "call_llm", new=model):
        result = asyncio.run(asyncio.wait_for(
            T.translate_text("原文职责", "CN", "EN"), timeout=1,
        ))
    assert result == expected
    assert model.await_count == 3


def test_repair_provider_failure_retains_previous_output():
    model = AsyncMock(side_effect=["Draft 残留", HTTPException(503, "unavailable")])
    with patch.object(LLMService, "call_llm", new=model):
        result = asyncio.run(T.translate_text("原文职责", "CN", "EN"))
    assert result == "Draft 残留"
    assert model.await_count == 2
