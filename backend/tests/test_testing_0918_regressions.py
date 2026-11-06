from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from pptx import Presentation
from pptx.util import Cm

from app.schemas.resume import ResumeData, ProjectItem, WorkItem
from app.services.anonymizer_service import AnonymizerService
from app.services.summarization_service import SummarizationService
from app.services.translator_service import TranslatorService
from app.services.smart_filler_service import SmartFillerService


@pytest.mark.parametrize("name", ["(2年11个月)", "（8个月）", "(4 years 2 months)", "1 year", "6 months"])
def test_duration_is_not_recovered_as_project(name):
    raw = f"项目经历\n2020/01-2022/11 {name}\n负责设计验证\n"
    result = SummarizationService.recover_embedded_projects(ResumeData(), raw)
    assert not result.project
    dirty = ResumeData(project=[ProjectItem(name=name, tasks="设计验证"),
                                ProjectItem(name="三年平台升级", tasks="真实项目")])
    assert [p.name for p in SummarizationService.sanitize_experience_data(dirty).project] == ["三年平台升级"]


def test_stated_experience_preserves_months_and_ongoing_work():
    source = ResumeData(total_exp="17年2个月", work=[WorkItem(period="2001.01 - Present")])
    assert TranslatorService.normalize_total_experience(source, "EN") == "17 years 2 months"
    assert TranslatorService.normalize_total_experience(source, "CN") == "17年2个月"


def test_unstated_experience_counts_union_and_present():
    now = datetime.now()
    source = ResumeData(work=[WorkItem(period=f"{now.year}.01 - Present"),
                              WorkItem(period=f"{now.year}.01 - Present")])
    expected = f"{now.month} months" if now.month < 12 else "1 year"
    if now.month == 1:
        expected = "1 month"
    assert TranslatorService.normalize_total_experience(source, "EN") == expected
    source.work = [WorkItem(period="2020.01-2020.03"), WorkItem(period="2020.03-2020.05"),
                   WorkItem(period="2021.01-2021.02")]
    assert TranslatorService.normalize_total_experience(source, "CN") == "7个月"


@pytest.mark.parametrize("surname, expected", [("祁", "Qi"), ("孔", "Kong"), ("洪", "Hong")])
def test_surname_outside_old_map_is_transliterated(surname, expected):
    assert AnonymizerService._chinese_name_to_pinyin(surname) == expected


def test_empty_language_level_preserves_runs():
    prs = Presentation()
    para = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_textbox(Cm(1), Cm(1), Cm(8), Cm(1)).text_frame.paragraphs[0]
    for text in ("{{lang_skills}}", " (", "{{lang_skills_level}}", ")"):
        para.add_run().text = text
    SmartFillerService.replace_text_in_paragraph(para, {"{{lang_skills}}": "普通话", "{{lang_skills_level}}": ""})
    assert para.text == "普通话"


@pytest.mark.asyncio
async def test_skill_translation_keeps_each_source_item(monkeypatch):
    calls = []
    async def translate(text, *args, **kwargs):
        calls.append(text)
        return {"接口设计": "Interface design", "故障分析": "Fault analysis"}.get(text, text)
    monkeypatch.setattr(TranslatorService, "translate_text", translate)
    monkeypatch.setattr(TranslatorService, "review_and_retranslate", AsyncMock(side_effect=lambda data, lang: data))
    result = await TranslatorService.translate_resume(ResumeData(tech_skills="Python；接口设计；故障分析"), "EN")
    assert "Interface design" in result.tech_skills
    assert "Fault analysis" in result.tech_skills
    assert "Python" in result.tech_skills
    assert "接口设计" in calls and "故障分析" in calls


def test_output_files_do_not_overwrite_same_candidate(monkeypatch, tmp_path):
    from app.services.pdf_converter import PdfConverterService
    monkeypatch.setattr(SmartFillerService, 'OUTPUT_DIR', str(tmp_path))
    monkeypatch.setattr(PdfConverterService, 'is_available', lambda: False)
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[6])
    data = ResumeData(name='孔先生', anonymized_name_cn='孔先生').model_dump()
    first = SmartFillerService._save_output_file(prs, data, 'new_cn')
    second = SmartFillerService._save_output_file(prs, data, 'new_cn')
    assert first['filename'] != second['filename']
    assert 'Kong' in first['filename']
    assert len(list(tmp_path.glob('*.pptx'))) == 2
