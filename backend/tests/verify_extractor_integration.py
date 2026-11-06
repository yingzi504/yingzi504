"""集成验证：mock LLM 返回异常格式，验证 extract_structure 不崩溃"""
import asyncio
import json
import sys

sys.path.insert(0, "d:/ai_resume/backend")

from app.services.extractor_service import ExtractorService
from app.services.llm_service import LLMService


async def test_case(name: str, mock_return):
    """运行一次抽取，mock LLM 返回指定内容"""
    original = LLMService.call_llm_json

    async def fake_call_llm_json(*args, **kwargs):
        if isinstance(mock_return, Exception):
            raise mock_return
        return mock_return

    LLMService.call_llm_json = staticmethod(fake_call_llm_json)
    try:
        result = await ExtractorService.extract_structure("张三的简历，工作5年，在华为做自动驾驶测试。")
        print(f"[{name}] OK -> name={result.name}, work={len(result.work)}, project={len(result.project)}")
    except Exception as e:
        print(f"[{name}] RAISED -> {type(e).__name__}: {str(e)[:150]}")
    finally:
        LLMService.call_llm_json = original


async def main():
    # C1: LLM 返回正常 dict
    await test_case("正常dict", {
        "name": "张三", "age": 30, "position": "测试工程师",
        "education": [{"school": "清华"}],
        "work": [{"company": "华为", "tasks": "负责测试"}],
        "project": [], "tech_skills": ["Python"],
    })

    # C2: LLM 返回 JSON 字符串（历史故障场景）
    await test_case("JSON字符串", json.dumps({
        "name": "李四", "age": 28,
        "education": [], "work": [{"company": "B", "tasks": ["t1", "t2"]}], "project": [],
    }))

    # C3: LLM 返回纯字符串（不可解析）
    await test_case("纯字符串", "抱歉，我无法提供JSON格式的回复")

    # C4: LLM 返回 list（根节点错误）
    await test_case("list根节点", [{"name": "x"}])

    # C5: education 为单个 dict、work 为 None
    await test_case("dict/None字段", {
        "name": "王五", "education": {"school": "北大"}, "work": None, "project": None,
    })

    # C6: LLM 抛 HTTPException（模拟 call_llm_json 内部 500）——应透传
    from fastapi import HTTPException
    await test_case("HTTPException透传", HTTPException(status_code=500, detail="JSON解析失败: xxx"))

    # C7: LLM 返回空 dict
    await test_case("空dict", {})


asyncio.run(main())
print("INTEGRATION DONE")
