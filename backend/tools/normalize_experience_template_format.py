"""Normalize spacing and responsibility alignment in vertical resume templates."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from lxml import etree


A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
A = "{" + A_NS + "}"
NS = {"a": A_NS}


def _text(paragraph) -> str:
    return "".join(paragraph.xpath(".//a:t/text()", namespaces=NS))


def _normalize_paragraph(paragraph, is_task: bool) -> None:
    ppr = paragraph.find(A + "pPr")
    if ppr is None:
        ppr = etree.Element(A + "pPr")
        paragraph.insert(0, ppr)
    ppr.set("algn", "l")
    ppr.set("marL", "0")
    ppr.set("indent", "0")
    for name in ("spcBef", "spcAft"):
        node = ppr.find(A + name)
        if node is None:
            node = etree.SubElement(ppr, A + name)
        for child in list(node):
            node.remove(child)
        etree.SubElement(node, A + "spcPts", val="0")
    if is_task:
        for name in ("buChar", "buFont", "buClrTx", "buSzTx", "buFontTx"):
            node = ppr.find(A + name)
            if node is not None:
                ppr.remove(node)
        if ppr.find(A + "buNone") is None:
            etree.SubElement(ppr, A + "buNone")


def patch_slide(xml_bytes: bytes) -> bytes:
    root = etree.fromstring(xml_bytes)
    for table in root.xpath(".//a:tbl", namespaces=NS):
        table_text = "".join(table.xpath(".//a:t/text()", namespaces=NS))
        module = "work" if "{{work." in table_text else "project" if "{{project." in table_text else None
        if module is None:
            continue
        task_placeholder = "{{" + module + ".tasks}}"
        for paragraph in table.xpath(".//a:p", namespaces=NS):
            _normalize_paragraph(paragraph, task_placeholder in _text(paragraph))
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def patch_pptx(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(destination, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.startswith("ppt/slides/slide") and info.filename.endswith(".xml"):
                data = patch_slide(data)
            dst.writestr(info, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    patch_pptx(args.source, args.destination)
