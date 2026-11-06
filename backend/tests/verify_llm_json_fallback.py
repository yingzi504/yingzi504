"""验证 llm_service 的 JSON 二次解析兜底"""
import asyncio
import json
import sys

sys.path.insert(0, "d:/ai_resume/backend")
from app.services.llm_service import LLMService


async def test_case(name: str, mock_content):
    """mock call_llm 返回内容，验证 call_llm_json 行为"""
    original = LLMService.call_llm

    async def fake_call_llm(*args, **kwargs):
        return mock_content

    LLMService.call_llm = staticmethod(fake_call_llm)
    try:
        result = await LLMService.call_llm_json(prompt="test", max_tokens=100)
        print(f"[{name}] OK -> type={type(result).__name__}, keys={list(result.keys())[:5]}")
    except Exception as e:
        print(f"[{name}] RAISED -> {type(e).__name__}: {str(e)[:150]}")
    finally:
        LLMService.call_llm = original


async def main():
    # 正常 JSON 对象
    await test_case("正常JSON", '{"name": "张三", "age": 30}')

    # Markdown 包裹
    await test_case("Markdown包裹", '```json\n{"name": "李四"}\n```')

    # 字符串包裹 JSON（历史故障场景：根节点是字符串）
    await test_case("字符串包裹JSON", '"{\\"name\\": \\"王五\\"}"')

    # 纯字符串（根节点 str 且内部不可解析）
    await test_case("纯字符串", '"抱歉，我无法提供JSON"')

    # 数组根节点
    await test_case("数组根节点", '[{"name": "x"}]')

    # 截断的 JSON
    await test_case("截断JSON", '{"name": "赵六", "age": 28, "education": [{"school": "清华"}], "work": [{"company": "华为"')

    # 完全不可解析
    await test_case("乱码", '这不是JSON内容，完全无法解析！！')


asyncio.run(main())
print("LLM SERVICE DONE")
