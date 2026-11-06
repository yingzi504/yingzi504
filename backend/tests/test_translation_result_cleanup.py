import os
import sys
import unittest
from pathlib import Path

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.translator_service import TranslatorService


class TranslationResultCleanupTests(unittest.TestCase):
    def test_language_skills_content_is_preserved(self):
        english = "Language skills: English and Japanese"
        chinese = "语言技能：英语和日语"

        self.assertEqual(
            TranslatorService._clean_translation_result(english, "EN"),
            english,
        )
        self.assertEqual(
            TranslatorService._clean_translation_result(chinese, "CN"),
            chinese,
        )

    def test_only_explicit_fences_and_translation_titles_are_removed(self):
        value = (
            "```text\n"
            "# Translation Result\n"
            "Language skills: English and Japanese\n"
            "```"
        )
        self.assertEqual(
            TranslatorService._clean_translation_result(value, "EN"),
            "Language skills: English and Japanese",
        )

        chinese = "## 翻译结果：\n语言技能：英语和日语"
        self.assertEqual(
            TranslatorService._clean_translation_result(chinese, "CN"),
            "语言技能：英语和日语",
        )

    def test_non_wrapper_markdown_heading_is_preserved(self):
        value = "# Senior Test Engineer\nResponsible for validation"
        self.assertEqual(
            TranslatorService._clean_translation_result(value, "EN"),
            value,
        )


if __name__ == "__main__":
    unittest.main()
