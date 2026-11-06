import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.resume import ResumeData
from app.services.anonymizer_service import AnonymizerService
from app.services.extractor_service import ExtractorService
from app.services.llm_service import LLMService
from app.services.parser_service import ParserService
from app.services.pipeline_service import PipelineService
from app.services.smart_filler_service import SmartFillerService
from app.services.summarization_service import SummarizationService
from app.services.translator_service import (
    TranslatorService,
)


class TranslationQualityGateTests(unittest.TestCase):
    def test_translate_text_stops_at_limit_with_latest_feedback(self):
        llm = AsyncMock(side_effect=[
            "Translated but still contains 中文",
            "Improved but still contains 职责",
            "Improved but still contains 职责",
            "Translated responsibilities",
        ])

        with (
            patch.object(LLMService, "call_llm", new=llm),
            patch.object(TranslatorService, "_wait_for_repair", new=AsyncMock()),
        ):
            result = asyncio.run(
                    TranslatorService.translate_text(
                        "中文职责",
                        "CN",
                        "EN",
                        context="工作内容",
                        field_path="work[0].tasks",
                    )
            )
        self.assertEqual(llm.await_count, 3)
        self.assertEqual(result, "Improved but still contains 职责")
        self.assertIn("Improved but still contains 职责", llm.await_args.kwargs["prompt"])
        self.assertIn('本轮待翻译残留：["职责"]', llm.await_args.kwargs["prompt"])
        self.assertIn("中文职责", llm.await_args.kwargs["prompt"])

    def test_empty_output_retries_without_losing_last_nonempty_translation(self):
        llm = AsyncMock(side_effect=["Senior 工程师", "", "", "Senior Engineer"])
        with (
            patch.object(LLMService, "call_llm", new=llm),
            patch.object(TranslatorService, "_wait_for_repair", new=AsyncMock()),
        ):
            result = asyncio.run(
                    TranslatorService.translate_text(
                        "中文职位", "CN", "EN", field_path="position"
                    )
            )
        self.assertEqual(result, "Senior 工程师")
        self.assertIn("Senior 工程师", llm.await_args.kwargs["prompt"])
        self.assertIn("empty_model_output", llm.await_args.kwargs["prompt"])

    def test_review_runs_final_audit_and_does_not_mutate_input(self):
        original = ResumeData(position="中文职位", language="CN")

        with patch.object(
            TranslatorService,
            "translate_text",
            new=AsyncMock(side_effect=["仍有中文", "还有残留", "Test Engineer"]),
        ) as translate:
            result = asyncio.run(
                TranslatorService.review_and_retranslate(original, "EN")
            )

        translate.assert_not_awaited()
        self.assertEqual(result.position, "中文职位")
        self.assertEqual(TranslatorService.audit_translation(result, "EN"), ["position"])
        self.assertEqual(original.position, "中文职位")

    def test_pipeline_repairs_quality_failure_then_generates_output(self):
        resume = ResumeData(position="中文职位", language="CN")
        task_id = PipelineService.create_task(
            file_id="quality-gate-test",
            target_language="EN",
            template_language="EN",
        )

        summarize = AsyncMock(side_effect=lambda data: data)
        fill = Mock(return_value={"pptx_path": "repaired.pptx", "filename": "repaired.pptx"})
        responses = iter(["残留一", "残留二", "残留三", "Engineer"])
        states = []

        async def model_response(**kwargs):
            current = PipelineService.get_task(task_id)
            states.append(current.to_status_dict())
            return next(responses)

        llm = AsyncMock(side_effect=model_response)

        try:
            with (
                patch.object(
                    PipelineService,
                    "_find_uploaded_file",
                    return_value="resume.docx",
                ),
                patch.object(
                    ParserService,
                    "parse_file",
                    new=AsyncMock(
                        return_value={"text_content": "private resume text"}
                    ),
                ),
                patch.object(
                    ExtractorService,
                    "extract_structure",
                    new=AsyncMock(return_value=resume),
                ),
                patch.object(
                    SummarizationService,
                    "recover_work_history",
                    return_value=resume,
                ),
                patch.object(
                    SummarizationService,
                    "recover_embedded_projects",
                    return_value=resume,
                ),
                patch.object(
                    AnonymizerService,
                    "anonymize_resume",
                    return_value=resume,
                ),
                patch.object(
                    LLMService, "call_llm", new=llm,
                ),
                patch.object(
                    SummarizationService,
                    "summarize_resume",
                    new=summarize,
                ),
                patch.object(
                    SmartFillerService,
                    "fill_template",
                    new=fill,
                ),
            ):
                asyncio.run(PipelineService.run_pipeline(task_id))

            task = PipelineService.get_task(task_id)
            self.assertIsNotNone(task)
            self.assertEqual(task.status, "completed")
            self.assertEqual(task.output_filename, "repaired.pptx")
            self.assertIsNone(task.error_code)
            self.assertEqual(task.resume_data["position"], "残留三")
            self.assertEqual(llm.await_count, 3)
            self.assertTrue(all(state["status"] == "processing" for state in states))
            self.assertIn("正在复核并修复翻译", states[-1]["message"])
            self.assertIsNone(task.translation_repair_message)
            summarize.assert_awaited_once()
            fill.assert_called_once()
        finally:
            with PipelineService._lock:
                PipelineService._tasks.pop(task_id, None)


if __name__ == "__main__":
    unittest.main()
