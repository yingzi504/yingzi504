import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.resume import extract_resume
from app.schemas.resume import ExtractionRequest, ResumeData, WorkItem
from app.services.extractor_service import ExtractorService


def test_extract_endpoint_applies_the_same_source_recovery_as_pipeline():
    raw_text = """WORKING EXPERIENCE
Audi China, Product Manager 2023/01-2023/04
Delivered cockpit products
Tencent Inc., Product Manager 2020/01-2021/12
Delivered map products
PROJECT EXPERIENCE
2023/01-2023/04 (Audi smart cockpit)
Project Name: Tencent Service
Delivered in-car applications
LANGUAGE AND SOFTWARE CAPABILITIES
English (IELTS 8)
EDUCATION / TRAINING
Example University
"""
    incomplete = ResumeData(
        total_exp="3 years",
        language="EN",
        work=[
            WorkItem(
                company="Audi China",
                period="2023/01-2023/04",
                role="Product Manager",
            )
        ],
    )

    with patch.object(
        ExtractorService,
        "extract_structure",
        new=AsyncMock(return_value=incomplete),
    ):
        response = asyncio.run(
            extract_resume(ExtractionRequest(raw_text=raw_text))
        )

    assert response.success
    assert [item.company for item in response.data.work] == [
        "Audi China",
        "Tencent Inc.",
    ]
    assert [item.name for item in response.data.project] == ["Tencent Service"]
    assert "LANGUAGE AND SOFTWARE CAPABILITIES" not in (
        response.data.project[0].tasks or ""
    )
