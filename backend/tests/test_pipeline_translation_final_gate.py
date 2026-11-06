import asyncio
import os
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.resume import ResumeData
from app.services.anonymizer_service import AnonymizerService
from app.services.extractor_service import ExtractorService
from app.services.parser_service import ParserService
from app.services.pipeline_service import PipelineService
from app.services.smart_filler_service import SmartFillerService
from app.services.summarization_service import SummarizationService
from app.services.translator_service import (
    TranslationQualityError,
    TranslatorService,
)


def quality_error(path, target="EN"):
    return TranslationQualityError(
        target,
        [{"path": path, "reason": "source_language_residue"}],
        last_output_usable=False,
    )


class PipelineTranslationFinalGateTests(unittest.TestCase):
    def _pipeline_patches(
        self,
        resume,
        *,
        translate_resume=None,
        summarize=None,
        sanitize=None,
        fill=None,
    ):
        return (
            patch.object(PipelineService, "_find_uploaded_file", return_value="resume.docx"),
            patch.object(
                ParserService,
                "parse_file",
                new=AsyncMock(return_value={"text_content": "private"}),
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
                TranslatorService,
                "translate_resume",
                new=translate_resume or AsyncMock(return_value=resume),
            ),
            patch.object(
                SummarizationService,
                "summarize_resume",
                new=summarize or AsyncMock(return_value=resume),
            ),
            patch.object(
                SummarizationService,
                "sanitize_experience_data",
                new=sanitize or Mock(return_value=resume),
            ),
            patch.object(
                SmartFillerService,
                "fill_template",
                new=fill or Mock(),
            ),
        )

    def _cleanup_task(self, task_id):
        with PipelineService._lock:
            PipelineService._tasks.pop(task_id, None)

    def test_technical_area_translation_failure_does_not_fallback(self):
        error = quality_error("technical_area", "CN")
        with patch.object(
            TranslatorService,
            "translate_text",
            new=AsyncMock(side_effect=error),
        ):
            with self.assertRaises(TranslationQualityError) as exc_info:
                asyncio.run(
                    PipelineService._resolve_target_technical_area(
                        "Test Engineer", "CN"
                    )
                )

        self.assertEqual(exc_info.exception.field_paths, ["technical_area"])

    def test_job_position_english_failure_stops_pipeline_before_ppt(self):
        resume = ResumeData(language="CN")
        task_id = PipelineService.create_task(
            file_id="job-position-failure",
            target_language="EN",
            template_language="EN",
            job_position="测试工程师",
        )
        review = AsyncMock(return_value=resume)
        fill = Mock()

        async def translate_position(text, source, target, **kwargs):
            if kwargs.get("field_path") == "job_position_en":
                raise quality_error("job_position_en")
            return "Test Engineer"

        patches = self._pipeline_patches(resume, fill=fill)
        try:
            with ExitStack() as stack:
                for pipeline_patch in patches:
                    stack.enter_context(pipeline_patch)
                stack.enter_context(patch.object(
                    PipelineService,
                    "_resolve_target_technical_area",
                    new=AsyncMock(return_value="Test Engineer"),
                ))
                stack.enter_context(patch.object(
                    TranslatorService,
                    "translate_text",
                    new=AsyncMock(side_effect=translate_position),
                ))
                stack.enter_context(patch.object(
                    TranslatorService,
                    "review_and_retranslate",
                    new=review,
                ))
                asyncio.run(PipelineService.run_pipeline(task_id))

            task = PipelineService.get_task(task_id)
            self.assertEqual(task.status, "failed")
            self.assertIn("job_position_en", task.error_message)
            self.assertEqual(task.error_code, "TRANSLATION_QUALITY_ERROR")
            self.assertEqual(
                task.error_details["field_paths"],
                ["job_position_en"],
            )
            status = task.to_status_dict()
            self.assertEqual(status["error_code"], "TRANSLATION_QUALITY_ERROR")
            self.assertEqual(
                status["error_details"]["field_paths"],
                ["job_position_en"],
            )
            review.assert_not_awaited()
            fill.assert_not_called()
        finally:
            self._cleanup_task(task_id)

    def test_final_audit_sees_all_derived_fields_and_is_last_text_step(self):
        resume = ResumeData(summary="English summary", language="EN")
        task_id = PipelineService.create_task(
            file_id="final-audit-order",
            target_language="EN",
            template_language="EN",
            job_position="Test Engineer",
        )
        events = []
        audited = {}

        async def translate_position(text, source, target, **kwargs):
            events.append(f"write:{kwargs.get('field_path')}")
            return text

        async def final_review(data, target):
            events.append("audit")
            audited["data"] = data.model_copy(deep=True)
            audited["returned"] = data.model_copy(deep=True)
            return audited["returned"]

        def fill_template(data, **kwargs):
            events.append("fill")
            audited["filled"] = data
            return {"pptx_path": "not-created.pptx", "filename": "result.pptx"}

        patches = self._pipeline_patches(
            resume,
            fill=Mock(side_effect=fill_template),
        )
        try:
            with ExitStack() as stack:
                for pipeline_patch in patches:
                    stack.enter_context(pipeline_patch)
                stack.enter_context(patch.object(
                    PipelineService,
                    "_resolve_target_technical_area",
                    new=AsyncMock(return_value="Testing"),
                ))
                stack.enter_context(patch.object(
                    TranslatorService,
                    "translate_text",
                    new=AsyncMock(side_effect=translate_position),
                ))
                stack.enter_context(patch.object(
                    TranslatorService,
                    "review_and_retranslate",
                    new=AsyncMock(side_effect=final_review),
                ))
                asyncio.run(PipelineService.run_pipeline(task_id))

            task = PipelineService.get_task(task_id)
            self.assertEqual(task.status, "completed")
            self.assertEqual(events, ["write:job_position", "audit", "fill"])
            self.assertEqual(audited["data"].technical_area, "Testing")
            self.assertEqual(audited["data"].job_position, "Test Engineer")
            self.assertEqual(audited["data"].job_position_en, "Test Engineer")
            self.assertIs(audited["filled"], audited["returned"])
        finally:
            self._cleanup_task(task_id)

    def test_summary_residue_does_not_block_ppt(self):
        translated = ResumeData(summary="English summary", language="EN")
        summarized = ResumeData(summary="摘要重新引入中文", language="EN")
        task_id = PipelineService.create_task(
            file_id="summary-residue",
            target_language="EN",
            template_language="EN",
        )
        fill = Mock(return_value={"pptx_path": "repaired.pptx", "filename": "repaired.pptx"})
        patches = self._pipeline_patches(
            translated,
            summarize=AsyncMock(return_value=summarized),
            sanitize=Mock(return_value=summarized),
            fill=fill,
        )
        try:
            with ExitStack() as stack:
                for pipeline_patch in patches:
                    stack.enter_context(pipeline_patch)
                stack.enter_context(patch.object(
                    TranslatorService,
                    "translate_text",
                    new=AsyncMock(side_effect=["仍有中文", "仍有残留", "Clean summary"]),
                ))
                asyncio.run(PipelineService.run_pipeline(task_id))

            task = PipelineService.get_task(task_id)
            self.assertEqual(task.status, "completed")
            self.assertIsNone(task.error_code)
            self.assertEqual(fill.call_args.args[0].summary, "摘要重新引入中文")
            fill.assert_called_once()
        finally:
            self._cleanup_task(task_id)


if __name__ == "__main__":
    unittest.main()
