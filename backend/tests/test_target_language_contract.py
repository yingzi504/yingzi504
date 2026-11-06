import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from app.api.resume import _resolve_target_language
from app.api.process import submit_pipeline_task
from app.schemas.resume import ResumeData
from app.schemas.task import PipelineSubmitRequest
from app.services.llm_service import LLMService
from app.services.pipeline_service import PipelineService
from app.services.translator_service import (
    TranslatorService,
    normalize_target_language,
)


class TargetLanguageContractTests(unittest.TestCase):
    def test_normalize_accepts_case_and_surrounding_spaces(self):
        self.assertEqual(normalize_target_language("en"), "EN")
        self.assertEqual(normalize_target_language(" EN "), "EN")
        self.assertEqual(normalize_target_language(" cn "), "CN")

    def test_normalize_rejects_empty_and_unknown_values(self):
        for value in ("FR", "", "  ", None):
            with self.subTest(value=value):
                with self.assertRaises(HTTPException) as exc_info:
                    normalize_target_language(value)
                self.assertEqual(exc_info.exception.status_code, 400)

    def test_resolver_prefers_template_but_validates_both_values(self):
        self.assertEqual(_resolve_target_language("cn", " en "), "EN")
        self.assertEqual(_resolve_target_language(" en ", None), "EN")

        for target, template in (("FR", "EN"), ("CN", "FR")):
            with self.subTest(target=target, template=template):
                with self.assertRaises(HTTPException) as exc_info:
                    _resolve_target_language(target, template)
                self.assertEqual(exc_info.exception.status_code, 400)

    def test_translate_text_validates_target_before_calling_llm(self):
        llm = AsyncMock(return_value="unused")
        with patch.object(LLMService, "call_llm", new=llm):
            with self.assertRaises(HTTPException) as exc_info:
                asyncio.run(
                    TranslatorService.translate_text(
                        "source text", "EN", "FR", field_path="summary"
                    )
                )

        self.assertEqual(exc_info.exception.status_code, 400)
        llm.assert_not_awaited()

    def test_internal_services_normalize_valid_target_values(self):
        text = asyncio.run(
            TranslatorService.translate_text("Already translated", "CN", " en ")
        )
        resume = asyncio.run(
            TranslatorService.translate_resume(ResumeData(language="CN"), " en ")
        )

        self.assertEqual(text, "Already translated")
        self.assertEqual(resume.language, "EN")

    def test_pipeline_submit_normalizes_languages_before_task_creation(self):
        request = PipelineSubmitRequest(
            file_id="language-contract-test",
            target_language=" en ",
            template_language=" cn ",
            department="TD",
        )
        with patch.object(PipelineService, "start_pipeline"):
            response = asyncio.run(submit_pipeline_task(request))

        task_id = response["data"]["task_id"]
        try:
            task = PipelineService.get_task(task_id)
            self.assertEqual(task.target_language, "EN")
            self.assertEqual(task.template_language, "CN")
        finally:
            with PipelineService._lock:
                PipelineService._tasks.pop(task_id, None)

    def test_pipeline_submit_rejects_invalid_target_even_with_template(self):
        request = PipelineSubmitRequest(
            file_id="language-contract-test",
            target_language="FR",
            template_language="EN",
            department="TD",
        )
        with self.assertRaises(HTTPException) as exc_info:
            asyncio.run(submit_pipeline_task(request))

        self.assertEqual(exc_info.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
