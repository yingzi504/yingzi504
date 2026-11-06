"""调试字符串包裹 JSON 场景"""
import sys
sys.path.insert(0, "d:/ai_resume/backend")
from app.services.llm_service import LLMService

# 模拟 LLM 返回：一个 JSON 字符串字面量（内部是对象）
text = '"{\\"name\\": \\"王五\\"}"'
print("RAW:", repr(text))
extracted = LLMService._extract_json(text)
print("extracted:", repr(extracted))
import json
p = json.loads(extracted)
print("parsed:", repr(p), type(p).__name__)
print("DONE")
