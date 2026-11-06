import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.resume import ResumeData
from app.services.llm_service import LLMService
from app.services.translator_service import TranslatorService


class TranslationResiduePolicyTests(unittest.TestCase):
    def test_target_english_detects_cjk_residue(self):
        for value in ("中文", "かな", "カナ", "한국어", "English 中文"):
            with self.subTest(value=value):
                self.assertTrue(
                    TranslatorService._has_language_residue(value, "EN")
                )
        self.assertFalse(
            TranslatorService._has_language_residue("English only", "EN")
        )

    def test_short_tokens_names_and_roles_are_not_missed(self):
        for value in ("PM", "Li", "Wu"):
            with self.subTest(value=value):
                self.assertTrue(
                    TranslatorService._has_language_residue(
                        value, "CN", "default"
                    )
                )

    def test_only_explicit_technical_terms_and_identifiers_are_allowed(self):
        allowed = (
            "AI",
            "Python",
            "Linux",
            "CANoe",
            "ADAS",
            "C++",
            "R&D",
            "ISO-26262",
        )
        for value in allowed:
            with self.subTest(value=value):
                self.assertFalse(
                    TranslatorService._has_language_residue(
                        value, "CN", "technical"
                    )
                )
                self.assertFalse(
                    TranslatorService._has_language_residue(
                        value, "CN", "default"
                    )
                )

        for value in ("PM", "Li", "Wu", "RESPONSIBLE", "Leadership"):
            with self.subTest(value=value):
                self.assertTrue(
                    TranslatorService._has_language_residue(
                        value, "CN", "technical"
                    )
                )

    def test_chinese_gate_allows_project_identifiers(self):
        values = (
            "PRD",
            "SAFe",
            "Epic",
            "PV/UV",
            "BR",
            "OS",
            "Clu39",
            "clu3B",
            "2B产品与2C产品",
        )
        for value in values:
            with self.subTest(value=value):
                self.assertFalse(
                    TranslatorService._has_language_residue(
                        value, "CN", "project_name"
                    )
                )

        summary = (
            "熟悉敏捷与SAFe方法论，擅长将Epic需求拆解为用户故事与验收标准，"
            "具备前后端产品规划能力，能提升用户体验及PV/UV；主导腾讯车联网B端产品上线"
        )
        self.assertFalse(
            TranslatorService._has_language_residue(summary, "CN", "default")
        )

    def test_chinese_gate_still_rejects_untranslated_natural_language(self):
        for value in (
            "负责 product delivery and requirements review",
            "Product Manager",
            "LANGUAGE AND SOFTWARE CAPABILITIES",
        ):
            with self.subTest(value=value):
                self.assertTrue(
                    TranslatorService._has_language_residue(
                        value, "CN", "default"
                    )
                )

    def test_audit_uses_each_registered_field_policy(self):
        resume = ResumeData(
            position="PM",
            tech_skills="Python, Linux, CANoe, ADAS",
            language="CN",
        )
        self.assertEqual(
            TranslatorService.audit_translation(resume, "CN"),
            ["position"],
        )

        resume.tech_skills = "RESPONSIBLE"
        self.assertEqual(
            TranslatorService.audit_translation(resume, "CN"),
            ["position", "tech_skills"],
        )

        resume = ResumeData(
            job_position="测试工程师",
            job_position_en="Test Engineer",
            language="CN",
        )
        self.assertEqual(TranslatorService.audit_translation(resume, "CN"), [])

    def test_technical_fields_skip_llm_only_for_allowed_terms(self):
        llm = AsyncMock(return_value="项目管理")
        with patch.object(LLMService, "call_llm", new=llm):
            protected = asyncio.run(
                TranslatorService.translate_text(
                    "Python, Linux, CANoe, ADAS",
                    "EN",
                    "CN",
                    field_path="tech_skills",
                    field_policy="technical",
                )
            )
            translated = asyncio.run(
                TranslatorService.translate_text(
                    "Project Management",
                    "EN",
                    "CN",
                    field_path="tech_skills",
                    field_policy="technical",
                )
            )

        self.assertEqual(protected, "Python, Linux, CANoe, ADAS")
        self.assertEqual(translated, "项目管理")
        self.assertEqual(llm.await_count, 1)

    def test_term_base_mapping_is_injected_into_prompt(self):
        llm = AsyncMock(return_value="人工智能")
        with patch.object(LLMService, "call_llm", new=llm):
            result = asyncio.run(
                TranslatorService.translate_text(
                    "Artificial Intelligence",
                    "EN",
                    "CN",
                    field_path="tech_skills",
                    field_policy="technical",
                )
            )

        self.assertEqual(result, "人工智能")
        system_prompt = llm.await_args.kwargs["system_prompt"]
        self.assertIn("Artificial Intelligence -> 人工智能", system_prompt)
        self.assertIn("Machine Learning -> 机器学习", system_prompt)


if __name__ == "__main__":
    unittest.main()
