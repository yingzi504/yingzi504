import ast
import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from app.api.resume import transform_resume as transform_endpoint
from app.api.resume import translate_resume as translate_endpoint
from app.schemas.resume import ResumeData, TransformRequest, TranslationRequest
from app.services.llm_service import LLMService
from app.services.translator_service import (
    TranslationQualityError,
    TranslatorService,
)


def quality_error():
    return TranslationQualityError(
        "EN",
        [{
            "path": "work[0].tasks",
            "reason": "source_language_residue",
        }],
        last_output_usable=False,
    )


class TranslationErrorContractTests(unittest.TestCase):
    def assert_quality_http_error(self, error):
        self.assertEqual(error.status_code, 422)
        self.assertEqual(error.detail["code"], "TRANSLATION_QUALITY_ERROR")
        self.assertEqual(error.detail["target_language"], "EN")
        self.assertEqual(error.detail["field_paths"], ["work[0].tasks"])
        self.assertEqual(
            error.detail["field_issues"],
            [{
                "path": "work[0].tasks",
                "reason": "source_language_residue",
            }],
        )
        self.assertFalse(error.detail["last_output_usable"])

    def test_translate_api_returns_structured_quality_error(self):
        request = TranslationRequest(
            resume_data=ResumeData(language="CN"),
            target_language="EN",
        )
        with patch.object(
            TranslatorService,
            "translate_resume",
            new=AsyncMock(side_effect=quality_error()),
        ):
            with self.assertRaises(HTTPException) as exc_info:
                asyncio.run(translate_endpoint(request))

        self.assert_quality_http_error(exc_info.exception)

    def test_transform_api_returns_structured_quality_error(self):
        request = TransformRequest(
            resume_data=ResumeData(language="CN"),
            target_language="EN",
            perform_anonymization=False,
        )
        with patch.object(
            TranslatorService,
            "translate_resume",
            new=AsyncMock(side_effect=quality_error()),
        ):
            with self.assertRaises(HTTPException) as exc_info:
                asyncio.run(transform_endpoint(request))

        self.assert_quality_http_error(exc_info.exception)

    def test_translation_logs_metadata_without_resume_or_model_content(self):
        private_source = "PRIVATE-SOURCE-中文"
        private_output = "PRIVATE-MODEL-中文"
        with (
            patch.object(
                LLMService,
                "call_llm",
                new=AsyncMock(side_effect=[private_output] * 3 + ["Translated"]),
            ),
            patch.object(
                TranslatorService, "_wait_for_repair", new=AsyncMock(),
            ),
            self.assertLogs(
                "app.services.translator_service", level="WARNING"
            ) as captured,
        ):
            result = asyncio.run(
                    TranslatorService.translate_text(
                        private_source,
                        "CN",
                        "EN",
                        field_path="work[0].tasks",
                    )
            )

        logs = "\n".join(captured.output)
        self.assertIn("work[0].tasks", logs)
        self.assertEqual(result, private_output)
        self.assertIn("attempt=3", logs)
        self.assertIn("reason=source_language_residue", logs)
        self.assertNotIn(private_source, logs)
        self.assertNotIn(private_output, logs)

    def test_translator_service_has_no_print_calls(self):
        service_path = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "services"
            / "translator_service.py"
        )
        tree = ast.parse(service_path.read_text(encoding="utf-8"))
        print_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ]
        self.assertEqual(print_calls, [])


if __name__ == "__main__":
    unittest.main()
