import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.translator_service import (
    TranslationQualityError,
    TranslatorService,
)


class TranslationTaskIntegrityTests(unittest.TestCase):
    def test_task_items_support_numbering_bullets_semicolons_and_lines(self):
        value = (
            "1. First\n"
            "2) Second\n"
            "(3) Third\n"
            "- Fourth\n"
            "* Fifth\n"
            "• Sixth；Seventh;Eighth"
        )
        self.assertEqual(
            TranslatorService._task_items(value),
            [
                "First",
                "Second",
                "Third",
                "Fourth",
                "Fifth",
                "Sixth",
                "Seventh",
                "Eighth",
            ],
        )
        self.assertEqual(
            TranslatorService._task_items("First line\nSecond line"),
            ["First line", "Second line"],
        )

    def test_long_task_list_preserves_count_and_order(self):
        source_items = [f"第{index}项职责" for index in range(1, 21)]
        source = "\n".join(
            f"{index}. {item}"
            for index, item in enumerate(source_items, start=1)
        )
        calls = []

        async def fake_translate(text, *args, field_path=None, **kwargs):
            calls.append((field_path, text))
            return f"Translated item {len(calls)}"

        with patch.object(
            TranslatorService,
            "translate_text",
            new=AsyncMock(side_effect=fake_translate),
        ):
            result = asyncio.run(
                TranslatorService._translate_task_list(
                    source,
                    "CN",
                    "EN",
                    "work experience",
                    field_path="work[0].tasks",
                )
            )

        output_items = TranslatorService._task_items(result)
        self.assertEqual(len(output_items), len(source_items))
        self.assertEqual(
            output_items,
            [f"Translated item {index}" for index in range(1, 21)],
        )
        self.assertEqual(
            [path for path, _text in calls],
            [f"work[0].tasks[{index}]" for index in range(20)],
        )
        self.assertEqual(
            [text for _path, text in calls],
            source_items,
        )

    def test_one_failed_item_marks_its_path_and_never_returns_partial_success(self):
        calls = []

        async def fake_translate(text, *args, field_path=None, **kwargs):
            calls.append(field_path)
            if field_path == "work[0].tasks[1]":
                raise TranslationQualityError(
                    "EN",
                    [{
                        "path": field_path,
                        "reason": "source_language_residue",
                    }],
                    last_output_usable=False,
                )
            return f"Translated {field_path}"

        with patch.object(
            TranslatorService,
            "translate_text",
            new=AsyncMock(side_effect=fake_translate),
        ):
            with self.assertRaises(TranslationQualityError) as exc_info:
                asyncio.run(
                    TranslatorService._translate_task_list(
                        "第一项；第二项；第三项",
                        "CN",
                        "EN",
                        "work experience",
                        field_path="work[0].tasks",
                    )
                )

        self.assertEqual(len(calls), 3)
        self.assertEqual(exc_info.exception.field_paths, ["work[0].tasks[1]"])
        self.assertEqual(
            exc_info.exception.field_issues[0]["reason"],
            "source_language_residue",
        )

    def test_empty_item_result_preserves_source_without_outer_retry(self):
        with patch.object(
            TranslatorService,
            "translate_text",
            new=AsyncMock(side_effect=["", "Repaired responsibility"]),
        ):
            result = asyncio.run(
                    TranslatorService._translate_task_list(
                        "单项职责",
                        "CN",
                        "EN",
                        "work experience",
                        field_path="work[0].tasks",
                    )
            )
        self.assertEqual(result, "单项职责")


if __name__ == "__main__":
    unittest.main()
