"""Update the CN resume template's colons, work font-size and wrap indentation.

This patches only PowerPoint text XML, preserving the original slide geometry,
relationships, media and editable native objects.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

from lxml import etree


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
A = "{%s}" % NS["a"]
CN_LABELS = ("姓名", "技术领域", "工作经验", "职责", "能力", "语言")
CN_TASK_TEXT_INDENT = "0"  # Responsibilities wrap flush-left with the first line.


def _paragraph_text(paragraph) -> str:
    return "".join(paragraph.xpath(".//a:t/text()", namespaces=NS))


def patch_slide_xml(xml_bytes: bytes) -> tuple[bytes, dict[str, int]]:
    root = etree.fromstring(xml_bytes)
    stats = {"colons": 0, "font_runs": 0, "task_indents": 0}

    # Chinese labels consistently use the full-width colon U+FF1A.
    label_pattern = re.compile(rf"^({'|'.join(map(re.escape, CN_LABELS))})\s*:")
    for paragraph in root.xpath(".//a:p", namespaces=NS):
        if not label_pattern.match(_paragraph_text(paragraph).strip()):
            continue
        for text_node in paragraph.xpath(".//a:t", namespaces=NS):
            if text_node.text and ":" in text_node.text:
                stats["colons"] += text_node.text.count(":")
                text_node.text = text_node.text.replace(":", "：")

    # Locate the CN work/project experience table row templates.
    for table in root.xpath(".//a:tbl", namespaces=NS):
        table_text = "".join(table.xpath(".//a:t/text()", namespaces=NS))
        is_work_table = "{{work." in table_text
        is_project_table = "{{project." in table_text
        if not (is_work_table or is_project_table):
            continue

        if is_work_table:
            # Explicit 11pt (1100 hundredths of a point) on every work-table run.
            for run in table.xpath(".//a:r", namespaces=NS):
                run_props = run.find(f"{A}rPr")
                if run_props is None:
                    run_props = etree.Element(f"{A}rPr")
                    run.insert(0, run_props)
                if run_props.get("sz") != "1100":
                    run_props.set("sz", "1100")
                    stats["font_runs"] += 1

            for props in table.xpath(".//a:defRPr | .//a:endParaRPr", namespaces=NS):
                props.set("sz", "1100")

        task_placeholder = "{{work.tasks}}" if is_work_table else "{{project.tasks}}"
        # Wrapped lines align with the first line's text after the literal "• ".
        for paragraph in table.xpath(".//a:p", namespaces=NS):
            if task_placeholder not in _paragraph_text(paragraph):
                continue
            para_props = paragraph.find(f"{A}pPr")
            if para_props is None:
                para_props = etree.Element(f"{A}pPr")
                paragraph.insert(0, para_props)
            para_props.set("marL", CN_TASK_TEXT_INDENT)
            para_props.set("indent", CN_TASK_TEXT_INDENT)
            stats["task_indents"] += 1

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True), stats


def patch_pptx(source: Path, destination: Path) -> dict[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    totals = {"colons": 0, "font_runs": 0, "task_indents": 0}

    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(destination, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.startswith("ppt/slides/slide") and info.filename.endswith(".xml"):
                data, stats = patch_slide_xml(data)
                for key, value in stats.items():
                    totals[key] += value
            dst.writestr(info, data)

    return totals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(patch_pptx(args.source, args.destination))


if __name__ == "__main__":
    main()
