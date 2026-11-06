import asyncio
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from docx import Document
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.jd_dictionaries import DEPARTMENT_CODES
from app.models.database import Base
from app.models.jd import JD
from app.schemas.jd import JDCreateRequest
from app.schemas.jd_conversion import (
    JDContent,
    JDConversionRequest,
    JDLocationRequest,
    JDPositionRecognitionRequest,
    JDRequirements,
)
from app.services.jd_conversion_service import (
    CN_OTHER_DUTY,
    EN_OTHER_DUTY,
    JDConversionService,
)
from app.services.jd_document_service import JDDocumentService
from app.services.llm_service import LLMService
from app.services.jd_service import JDService


def sample_content() -> JDContent:
    return JDContent(
        title_cn="自动驾驶系统工程师",
        title_en="ADAS System Engineer",
        location_cn="合肥",
        location_en="Hefei",
        department="TD",
        category="technical",
        responsibilities_cn=["负责传感器标定", CN_OTHER_DUTY],
        responsibilities_en=["Own sensor calibration", EN_OTHER_DUTY],
        requirements=JDRequirements.model_validate(
            {
                "education": {"cn": ["本科及以上学历"], "en": ["Bachelor degree or above"]},
                "experience": {"cn": ["三年相关经验"], "en": ["Three years of relevant experience"]},
                "required_skills": {"cn": ["熟悉CANoe"], "en": ["Proficient with CANoe"]},
                "language": {"cn": ["英语流利"], "en": ["Fluent English"]},
                "preferred": {"cn": ["雷达经验优先"], "en": ["Radar experience is preferred"]},
                "soft_skills": {"cn": ["具备协作能力"], "en": ["Strong collaboration skills"]},
            }
        ),
    )


class JDConversionTests(unittest.TestCase):
    def test_conversion_request_accepts_source_or_manual_target(self):
        with self.assertRaises(ValidationError):
            JDConversionRequest()
        with self.assertRaises(ValidationError):
            JDConversionRequest(file_id="file", source_text="text")
        self.assertEqual(JDConversionRequest(source_text="JD text").source_text, "JD text")
        manual = JDConversionRequest(
            target_position="ADAS System Engineer",
            target_position_source="manual",
        )
        self.assertEqual(manual.target_position, "ADAS System Engineer")

        with self.assertRaises(ValidationError):
            JDConversionRequest(target_position_source="manual")
        with self.assertRaises(ValidationError):
            JDConversionRequest(source_text="ADAS Engineer", target_position_source="filename")

    def test_target_position_resolution_and_generation_modes(self):
        request = JDConversionRequest(
            file_id="upload-1",
            original_filename="JD_IAV-CN_ADAS System Engineer_CN+EN_20250428.docx",
            target_position_source="filename",
        )
        self.assertEqual(
            JDConversionService._filename_target_position(request.original_filename),
            "ADAS System Engineer",
        )
        self.assertEqual(JDConversionService._detect_generation_mode("ADAS System Engineer", request), "title_only")
        self.assertEqual(
            JDConversionService._detect_generation_mode(
                "Responsibilities: own system design. Requirements: relevant engineering experience. " * 8,
                request,
            ),
            "full_jd",
        )
        self.assertEqual(
            JDConversionService._detect_generation_mode(
                "Own system requirements and vehicle integration for an ADAS product.",
                request,
            ),
            "partial_jd",
        )

    def test_position_recognition_request_validation(self):
        filename_request = JDPositionRecognitionRequest(
            file_id="upload-1",
            original_filename="JD_ADAS Engineer.docx",
            target_position_source="filename",
        )
        self.assertEqual(filename_request.target_position_source, "filename")
        content_request = JDPositionRecognitionRequest(
            source_text="ADAS Engineer responsibilities",
            target_position_source="content",
        )
        self.assertEqual(content_request.source_text, "ADAS Engineer responsibilities")

        with self.assertRaises(ValidationError):
            JDPositionRecognitionRequest(target_position_source="content")
        with self.assertRaises(ValidationError):
            JDPositionRecognitionRequest(file_id="upload-1", target_position_source="filename")

    def test_filename_target_position_recognition(self):
        request = JDPositionRecognitionRequest(
            file_id="upload-1",
            original_filename="JD_IAV-CN_ADAS System Engineer_CN+EN_20250428.docx",
            target_position_source="filename",
        )
        result = asyncio.run(JDConversionService.recognize_target_position(request))
        self.assertEqual(result, "ADAS System Engineer")

    def test_content_target_position_recognition(self):
        original_call = LLMService.call_llm_json

        async def fake_call(**_kwargs):
            return {"title_cn": "自动驾驶算法工程师", "title_en": "Autonomous Driving Algorithm Engineer"}

        try:
            LLMService.call_llm_json = staticmethod(fake_call)
            request = JDPositionRecognitionRequest(
                source_text="负责自动驾驶感知算法研发",
                target_position_source="content",
                output_language="CN",
            )
            result = asyncio.run(JDConversionService.recognize_target_position(request))
            self.assertEqual(result, "自动驾驶算法工程师")
        finally:
            LLMService.call_llm_json = original_call

    def test_manual_target_position_is_authoritative(self):
        original_call = LLMService.call_llm_json

        async def fake_call(**_kwargs):
            raw = sample_content().model_dump()
            raw["title_en"] = "Model Chosen Title"
            return raw

        try:
            LLMService.call_llm_json = staticmethod(fake_call)
            request = JDConversionRequest(
                target_position="ADAS Platform Owner",
                target_position_source="manual",
                output_language="CNEN",
            )
            content = asyncio.run(JDConversionService._standardize("", request))
            self.assertEqual(content.title_en, "ADAS Platform Owner")
        finally:
            LLMService.call_llm_json = original_call

    def test_edited_recognized_target_position_is_authoritative(self):
        original_call = LLMService.call_llm_json

        async def fake_call(**_kwargs):
            raw = sample_content().model_dump()
            raw["title_en"] = "Model Chosen Title"
            return raw

        try:
            LLMService.call_llm_json = staticmethod(fake_call)
            request = JDConversionRequest(
                source_text="Responsibilities: own ADAS platform delivery.",
                target_position="Senior ADAS Platform Owner",
                target_position_source="content",
                output_language="EN",
            )
            content = asyncio.run(JDConversionService._standardize(request.source_text or "", request))
            self.assertEqual(content.title_en, "Senior ADAS Platform Owner")
            self.assertEqual(JDConversionService._display_target_position(content, request), "Senior ADAS Platform Owner")
        finally:
            LLMService.call_llm_json = original_call

    def test_bilingual_target_position_override_updates_both_titles(self):
        raw = sample_content().model_dump()
        JDConversionService._apply_requested_target_position(
            raw,
            "高级自动驾驶平台负责人 / Senior ADAS Platform Owner",
        )
        self.assertEqual(raw["title_cn"], "高级自动驾驶平台负责人")
        self.assertEqual(raw["title_en"], "Senior ADAS Platform Owner")

    def test_missing_source_location_pauses_and_manual_location_resumes(self):
        original_call = LLMService.call_llm_json
        original_generate = JDDocumentService.generate

        async def fake_call(**_kwargs):
            raw = sample_content().model_dump()
            raw["location_cn"] = "Model Invented City"
            raw["location_en"] = "Model Invented City"
            return raw

        def fake_generate(_content, _language):
            return {
                "filename": "jd.docx",
                "docx_path": "jd.docx",
                "pdf_path": None,
                "pdf_available": False,
            }

        try:
            LLMService.call_llm_json = staticmethod(fake_call)
            request = JDConversionRequest(
                target_position="ADAS System Engineer",
                target_position_source="manual",
                output_language="CNEN",
            )
            task = JDConversionService.create_task(request)
            asyncio.run(JDConversionService.run_task(task.task_id))

            self.assertEqual(task.status, "awaiting_input")
            self.assertEqual(task.current_step, "awaiting_location")
            self.assertEqual(task.progress, 75)
            self.assertEqual(task.content.location_cn, "")
            self.assertEqual(task.content.location_en, "")
            self.assertEqual(task.status_dict()["required_input"]["field"], "location")

            JDDocumentService.generate = staticmethod(fake_generate)
            asyncio.run(JDConversionService.provide_location(task, "上海 / Shanghai"))
            self.assertEqual(task.status, "completed")
            self.assertEqual(task.content.location_cn, "上海")
            self.assertEqual(task.content.location_en, "Shanghai")
            self.assertIsNone(task.status_dict()["required_input"])
        finally:
            LLMService.call_llm_json = original_call
            JDDocumentService.generate = original_generate

    def test_location_request_rejects_blank_value(self):
        self.assertEqual(JDLocationRequest(location=" Shanghai ").location, "Shanghai")
        with self.assertRaises(ValidationError):
            JDLocationRequest(location="   ")

    def test_location_keeps_region_only(self):
        content = sample_content()
        content.location_cn = "\u4e2d\u56fd / \u5408\u80a5\uff08onsite\uff09"
        content.location_en = "Hefei, China (onsite)"
        asyncio.run(JDConversionService._normalize_location_pair(content))
        self.assertEqual(content.location_cn, "\u5408\u80a5")
        self.assertEqual(content.location_en, "Hefei")

        with self.assertRaises(ValueError):
            asyncio.run(JDConversionService._set_manual_location(content, "China (onsite)"))

    def test_source_location_flag_preserves_detected_location(self):
        original_call = LLMService.call_llm_json

        async def fake_call(**_kwargs):
            raw = sample_content().model_dump()
            raw["source_location_found"] = True
            return raw

        try:
            LLMService.call_llm_json = staticmethod(fake_call)
            request = JDConversionRequest(
                source_text="Work location: Hefei. Responsibilities and requirements are provided.",
                target_position_source="content",
            )
            content, found = asyncio.run(
                JDConversionService._standardize_with_analysis(request.source_text, request)
            )
            self.assertTrue(found)
            self.assertTrue(content.location_cn)
            self.assertEqual(content.location_en, "Hefei")
        finally:
            LLMService.call_llm_json = original_call

    def test_frontend_library_aliases_are_accepted(self):
        request = JDCreateRequest(
            position="ADAS Engineer",
            department="IT",
            category="technical",
            language="zh",
            content="content",
            tags=["ADAS"],
        )
        self.assertEqual(request.title, "ADAS Engineer")
        self.assertEqual(request.language, "CN")
        self.assertEqual(request.description, "content")

    def test_department_dictionary_is_fixed_and_shared_with_frontend(self):
        self.assertEqual(len(DEPARTMENT_CODES), len(set(DEPARTMENT_CODES)))
        self.assertEqual(DEPARTMENT_CODES.count("TV-A"), 1)
        self.assertEqual(JDConversionRequest(source_text="JD", department="CSO-V").department, "CSO-V")
        self.assertEqual(JDConversionRequest(source_text="JD", department="").department, "")

        with self.assertRaises(ValidationError):
            JDConversionRequest(source_text="JD", department="Engineering")
        with self.assertRaises(ValidationError):
            JDCreateRequest(
                position="ADAS Engineer",
                department="Engineering",
                category="technical",
                content="content",
            )

        frontend_file = (
            Path(__file__).resolve().parents[2]
            / "frontend"
            / "src"
            / "utils"
            / "departments.ts"
        )
        frontend_codes = re.findall(
            r"^\s+'([^']+)',?$",
            frontend_file.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        self.assertEqual(frontend_codes, list(DEPARTMENT_CODES))

    def test_normalization_enforces_single_final_other_duty(self):
        content = sample_content()
        content.responsibilities_cn.append("负责上级安排的其他工作")
        content.responsibilities_en.append("Other duties assigned by the manager")
        normalized = asyncio.run(JDConversionService.normalize_content(content))
        self.assertEqual(normalized.responsibilities_cn[-1], CN_OTHER_DUTY)
        self.assertEqual(normalized.responsibilities_en[-1], EN_OTHER_DUTY)
        self.assertEqual(normalized.responsibilities_cn.count(CN_OTHER_DUTY), 1)
        self.assertEqual(normalized.responsibilities_en.count(EN_OTHER_DUTY), 1)

    def test_save_final_conversion_updates_same_task(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        try:
            task = SimpleNamespace(
                task_id="task-1",
                content=sample_content(),
                request=SimpleNamespace(output_language="CNEN"),
            )
            created = JDService.save_final_conversion(session, task)
            self.assertEqual(created.department, "TD")
            self.assertEqual(created.category, "technical")
            self.assertEqual(created.language, "CNEN")
            self.assertIsNotNone(created.structuredData)

            task.content.title_en = "Updated ADAS System Engineer"
            updated = JDService.save_final_conversion(session, task)
            self.assertEqual(updated.id, created.id)
            self.assertIn("Updated", updated.title)
            self.assertEqual(session.query(JD).count(), 1)
        finally:
            session.close()

    def test_templates_preserve_required_order(self):
        cases = [
            ("CN", ("岗位职责：", "任职要求：")),
            ("EN", ("Your Tasks:", "Your Skills:")),
            ("CNEN", ("Your Tasks:", "岗位职责：", "Your Skills:", "任职要求：")),
        ]
        original_output_dir = settings.output_dir
        original_converter = JDDocumentService._convert_docx_to_pdf
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                settings.output_dir = temp_dir
                JDDocumentService._convert_docx_to_pdf = staticmethod(lambda _: None)
                content = asyncio.run(JDConversionService.normalize_content(sample_content()))
                cn_requirements = []
                for key in JDDocumentService.REQUIREMENT_ORDER:
                    cn_requirements.extend(getattr(content.requirements, key).cn)
                self.assertTrue(content.responsibilities_cn[-1].endswith("\u3002"))
                self.assertTrue(cn_requirements[-1].endswith("\u3002"))
                self.assertTrue(all(item.endswith("\uff1b") for item in content.responsibilities_cn[:-1]))
                self.assertTrue(all(item.endswith("\uff1b") for item in cn_requirements[:-1]))
                en_items = list(content.responsibilities_en)
                for key in JDDocumentService.REQUIREMENT_ORDER:
                    en_items.extend(getattr(content.requirements, key).en)
                self.assertTrue(all(item.endswith(".") for item in en_items))
                content.location_cn = "\u4e2d\u56fd / \u5408\u80a5\uff08onsite\uff09"
                content.location_en = "Hefei, China (onsite)"
                for language, headings in cases:
                    with self.subTest(language=language):
                        result = JDDocumentService.generate(content, language)
                        output = Path(result["docx_path"])
                        self.assertTrue(output.exists())
                        language_label = "CN+EN" if language == "CNEN" else language
                        self.assertRegex(
                            output.name,
                            rf"^JD_IAV-CN_.+_{re.escape(language_label)}_\d{{8}}\.docx$",
                        )
                        self.assertNotRegex(output.name, r"_\d{8}_\d{6}\.docx$")
                        document = Document(output)
                        paragraphs = [" ".join(p.text.split()) for p in document.paragraphs if p.text.strip()]
                        content_paragraphs = [
                            re.sub(r"[；。.!?]+$", "", paragraph)
                            for paragraph in paragraphs
                        ]
                        all_paragraphs = [p.text.strip() for p in document.paragraphs]
                        location_index = 2 if language == "CNEN" else 1
                        location_paragraph = document.paragraphs[location_index]
                        self.assertTrue(location_paragraph._p.xpath(".//w:drawing"))
                        self.assertNotIn("China", location_paragraph.text)
                        self.assertNotIn("onsite", location_paragraph.text.lower())
                        if language in ("CN", "CNEN"):
                            self.assertIn("\u5408\u80a5", location_paragraph.text)
                        if language in ("EN", "CNEN"):
                            self.assertIn("Hefei", location_paragraph.text)

                        heading_positions = [paragraphs.index(heading) for heading in headings]
                        self.assertEqual(heading_positions, sorted(heading_positions))
                        requirement_heading = "任职要求：" if language == "CN" else "Your Skills:"
                        requirement_index = all_paragraphs.index(requirement_heading)
                        self.assertEqual(all_paragraphs[requirement_index - 1], "")
                        if language in ("CN", "CNEN"):
                            self.assertIn(CN_OTHER_DUTY, paragraphs)
                        if language in ("EN", "CNEN"):
                            self.assertIn(EN_OTHER_DUTY, paragraphs)

                        ordered_cn = [
                            "本科及以上学历",
                            "三年相关经验",
                            "熟悉CANoe",
                            "英语流利",
                            "雷达经验优先",
                            "具备协作能力",
                        ]
                        ordered_en = [
                            "Bachelor degree or above",
                            "Three years of relevant experience",
                            "Proficient with CANoe",
                            "Fluent English",
                            "Radar experience is preferred",
                            "Strong collaboration skills",
                        ]
                        if language in ("CN", "CNEN"):
                            indexes = [content_paragraphs.index(item) for item in ordered_cn]
                            self.assertEqual(indexes, sorted(indexes))
                        if language in ("EN", "CNEN"):
                            indexes = [content_paragraphs.index(item) for item in ordered_en]
                            self.assertEqual(indexes, sorted(indexes))
        finally:
            settings.output_dir = original_output_dir
            JDDocumentService._convert_docx_to_pdf = original_converter


if __name__ == "__main__":
    unittest.main()
