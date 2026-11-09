from pathlib import Path

import pytest

from app.services.pdf_converter import PdfConverterService


def test_is_available_with_powerpoint_fallback(monkeypatch):
    monkeypatch.setattr(PdfConverterService, "find_libreoffice", lambda: None)
    monkeypatch.setattr(PdfConverterService, "has_powerpoint", lambda: True)
    assert PdfConverterService.is_available() is True


def test_convert_uses_powerpoint_when_libreoffice_is_missing(monkeypatch, tmp_path):
    source = tmp_path / "resume.pptx"
    source.write_bytes(b"pptx fixture")
    destination = tmp_path / "pdf"
    calls = []

    monkeypatch.setattr(PdfConverterService, "find_libreoffice", lambda: None)
    monkeypatch.setattr(PdfConverterService, "has_powerpoint", lambda: True)

    def fake_powerpoint(pptx_path, expected_pdf):
        calls.append((pptx_path, expected_pdf))
        Path(expected_pdf).write_bytes(b"%PDF fixture")
        return expected_pdf

    monkeypatch.setattr(
        PdfConverterService, "_convert_with_powerpoint", fake_powerpoint
    )
    result = PdfConverterService.convert_pptx_to_pdf(
        str(source), str(destination)
    )

    assert Path(result).read_bytes() == b"%PDF fixture"
    assert calls == [(str(source), str(destination / "resume.pdf"))]


def test_convert_reports_missing_converter(monkeypatch, tmp_path):
    source = tmp_path / "resume.pptx"
    source.write_bytes(b"pptx fixture")
    monkeypatch.setattr(PdfConverterService, "find_libreoffice", lambda: None)
    monkeypatch.setattr(PdfConverterService, "has_powerpoint", lambda: False)

    with pytest.raises(FileNotFoundError, match="PDF 转换器"):
        PdfConverterService.convert_pptx_to_pdf(str(source))
