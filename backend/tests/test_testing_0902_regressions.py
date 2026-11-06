from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.resume import ResumeData, WorkItem
from app.services.anonymizer_service import AnonymizerService
from app.services.summarization_service import SummarizationService
from app.services.translator_service import TranslatorService


def test_bilingual_name_uses_parenthesized_chinese_surname():
    source = ResumeData(name="Charles Yang (杨超)", language="EN")
    result = AnonymizerService.anonymize_resume(source)
    assert result.name == "Mr. Yang"
    assert result.anonymized_name_cn == "杨先生"


def test_charles_style_sections_keep_employers_out_of_projects():
    source = """EDUCATION
2010/01-2012/01 Example University
WORKING EXPERIENCE
Audi China, Product Manager, Beijing 2023/01-2023/04
Delivered cockpit products
Capgemini China, Product Manager, Beijing 2021/12-2022/09
Delivered finance products
Zhimei Life (Beijing) Technology Co., Ltd., Product Manager, Beijing 2018/09-2019/12
Delivered marketplace products
PROJECT EXPERIENCE
2023/01-2023/04 (Audi smart cockpit)
Project Name: Tencent Service
Delivered in-car applications
"""
    resume = ResumeData(work=[
        WorkItem(company="Audi China", period="2023/01-2023/04"),
        WorkItem(
            company="Zhimei Life (Beijing) Technology Co.",
            period="2018/09-2019/12",
            role="Ltd.",
        ),
    ])
    result = SummarizationService.recover_work_history(resume, source)
    result = SummarizationService.recover_embedded_projects(result, source)
    result = SummarizationService.recover_work_history(result, source)
    result = SummarizationService.recover_embedded_projects(result, source)
    assert [item.company for item in result.work] == [
        "Audi China",
        "Capgemini China",
        "Zhimei Life (Beijing) Technology Co., Ltd.",
    ]
    assert result.work[-1].role == "Product Manager"
    assert [item.name for item in result.project] == ["Tencent Service"]
    assert all("University" not in (item.name or "") for item in result.project)


def test_total_experience_is_stable_across_languages():
    hmi = ResumeData(total_exp="3年", work=[
        WorkItem(period="2019.06 - 2021.07"),
        WorkItem(period="2021.08 - 2023.03"),
    ])
    fan = ResumeData(total_exp="1年", work=[WorkItem(period="2021.06 - 2021.11")])
    assert TranslatorService.normalize_total_experience(hmi, "CN") == "3年"
    assert TranslatorService.normalize_total_experience(hmi, "EN") == "3 years"
    assert TranslatorService.normalize_total_experience(fan, "CN") == "1年"
    assert TranslatorService.normalize_total_experience(fan, "EN") == "1 year"