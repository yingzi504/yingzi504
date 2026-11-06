import asyncio
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.resume import EducationItem, ProjectItem, ResumeData, WorkItem
from app.services.translator_service import TranslatorService


class TranslationFieldRegistryTests(unittest.TestCase):
    def test_registry_classifies_every_resume_schema_field(self):
        translated_root = {
            attr for attr, _context, _technical in TranslatorService._ROOT_TRANSLATION_FIELDS
        }
        nested_containers = set(TranslatorService._NESTED_TRANSLATION_FIELDS)
        excluded = set(TranslatorService._EXCLUDED_RESUME_FIELDS)

        self.assertFalse(translated_root & nested_containers)
        self.assertFalse(translated_root & excluded)
        self.assertFalse(nested_containers & excluded)
        self.assertEqual(
            translated_root | nested_containers | excluded,
            set(ResumeData.model_fields),
        )

        nested_models = {
            "education": EducationItem,
            "work": WorkItem,
            "project": ProjectItem,
        }
        for collection_name, model in nested_models.items():
            with self.subTest(collection=collection_name):
                registered = {
                    attr
                    for attr, _context, _technical
                    in TranslatorService._NESTED_TRANSLATION_FIELDS[collection_name]
                }
                self.assertEqual(registered, set(model.model_fields))

    def test_initial_translation_and_audit_share_the_registry(self):
        source = ResumeData(
            name="张先生",
            anonymized_name="张先生",
            anonymized_name_cn="张先生",
            phone="13800138000",
            email="candidate@example.com",
            location="地点",
            age=30,
            birth_date="出生日期",
            gender="male",
            position="职位",
            job_position="目标岗位",
            job_position_en="英文岗位",
            technical_area="技术领域",
            total_exp="2年",
            summary="个人简介",
            tech_skills="技术技能",
            lang_skills="语言技能",
            lang_skills_level="语言水平",
            training_exp="培训经历",
            education=[
                EducationItem(
                    period="2020年1月至2021年1月",
                    school="学校",
                    degree="学位",
                    major="专业",
                )
            ],
            work=[
                WorkItem(
                    period="2020年1月至2021年1月",
                    company="公司",
                    role="工作角色",
                    tasks="工作职责",
                )
            ],
            project=[
                ProjectItem(
                    period="2020年1月至2021年1月",
                    company="项目公司",
                    name="项目名称",
                    role="项目角色",
                    tasks="项目职责",
                )
            ],
            language="CN",
            is_anonymized=True,
        )
        translated_paths = []

        async def fake_translate(
            text,
            source_lang,
            target_lang,
            context=None,
            field_path=None,
            field_policy="default",
        ):
            translated_paths.append(field_path)
            return f"Translated {field_path}"

        with (
            patch.object(
                TranslatorService,
                "_translate_name",
                new=AsyncMock(return_value="Mr. Zhang"),
            ),
            patch.object(
                TranslatorService,
                "translate_text",
                new=AsyncMock(side_effect=fake_translate),
            ),
        ):
            result = asyncio.run(TranslatorService.translate_resume(source, "EN"))

        self.assertEqual(TranslatorService.audit_translation(result, "EN"), [])
        for path, obj, attr, _context, _technical in TranslatorService._translation_fields(
            result
        ):
            with self.subTest(path=path):
                value = str(getattr(obj, attr, "") or "")
                self.assertIsNone(re.search(r"[\u4e00-\u9fff]", value))

        self.assertIn("birth_date", translated_paths)
        self.assertIn("job_position", translated_paths)
        self.assertIn("job_position_en", translated_paths)
        self.assertIn("education[0].school", translated_paths)
        self.assertIn("work[0].tasks", translated_paths)
        self.assertIn("project[0].tasks", translated_paths)
        self.assertEqual(result.anonymized_name, "Mr. Zhang")
        self.assertEqual(result.anonymized_name_cn, "张先生")
        self.assertEqual(result.phone, source.phone)
        self.assertEqual(result.email, source.email)
        self.assertEqual(result.age, source.age)
        self.assertEqual(result.gender, source.gender)
        self.assertTrue(result.is_anonymized)
        self.assertEqual(source.position, "职位")

    def test_distinct_anonymized_aliases_are_not_overwritten(self):
        source = ResumeData(
            name="张先生",
            anonymized_name="Protected Alias",
            anonymized_name_cn="张先生",
            language="CN",
            is_anonymized=True,
        )

        with patch.object(
            TranslatorService,
            "_translate_name",
            new=AsyncMock(return_value="Mr. Zhang"),
        ):
            result = asyncio.run(TranslatorService.translate_resume(source, "EN"))

        self.assertEqual(result.name, "Mr. Zhang")
        self.assertEqual(result.anonymized_name, "Protected Alias")
        self.assertEqual(result.anonymized_name_cn, "张先生")

    def test_chinese_anonymized_name_bypasses_name_llm(self):
        source = ResumeData(
            name="Mr. Zhang",
            anonymized_name="Mr. Zhang",
            anonymized_name_cn="张先生",
            language="EN",
            is_anonymized=True,
        )
        translate_name = AsyncMock(
            side_effect=AssertionError("name LLM should not be called")
        )

        with patch.object(
            TranslatorService,
            "_translate_name",
            new=translate_name,
        ):
            result = asyncio.run(TranslatorService.translate_resume(source, "CN"))

        translate_name.assert_not_awaited()
        self.assertEqual(result.name, "张先生")
        self.assertEqual(result.anonymized_name, "张先生")
        self.assertEqual(result.anonymized_name_cn, "张先生")


if __name__ == "__main__":
    unittest.main()
