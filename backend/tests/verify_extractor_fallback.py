"""临时验证脚本：验证 extractor 类型兜底逻辑与 ResumeData 容错性"""
import json
import sys

sys.path.insert(0, "d:/ai_resume/backend")
from app.schemas.resume import ResumeData


def normalize(extracted_data):
    """模拟 extractor_service.py 中的兜底逻辑"""
    if isinstance(extracted_data, str):
        try:
            parsed = json.loads(extracted_data)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        extracted_data = parsed
    if not isinstance(extracted_data, dict):
        extracted_data = {}
    for field in ("education", "work", "project"):
        val = extracted_data.get(field)
        if val is None:
            extracted_data[field] = []
        elif not isinstance(val, list):
            extracted_data[field] = [val]
    for field in ("work", "project"):
        for item in extracted_data.get(field, []):
            if isinstance(item, dict):
                tasks = item.get("tasks")
                if isinstance(tasks, list):
                    item["tasks"] = "; ".join(str(t) for t in tasks if t)
    return extracted_data


# T1: 正常 dict
d1 = {"name": "张三", "age": 30, "education": [{"school": "清华"}], "work": [], "project": []}
r1 = ResumeData(**normalize(d1))
print("T1 OK:", r1.name, r1.age, len(r1.education))

# T2: LLM 返回 JSON 字符串（可解析）
s2 = json.dumps({"name": "李四", "age": 28, "education": [], "work": [], "project": []})
r2 = ResumeData(**normalize(s2))
print("T2 OK:", r2.name, r2.age)

# T3: LLM 返回不可解析字符串 -> 回退空结构
r3 = ResumeData(**normalize("抱歉，我无法提供JSON"))
print("T3 OK: fallback empty, language =", r3.language)

# T4: education 是单个 dict、work/project 为 None
d4 = {"name": "王五", "education": {"school": "北大"}, "work": None, "project": None}
r4 = ResumeData(**normalize(d4))
print("T4 OK:", len(r4.education), r4.education[0].school)

# T5: work 的 tasks 是 list
d5 = {"name": "赵六", "work": [{"company": "A", "tasks": ["任务1", "任务2"]}], "project": []}
r5 = ResumeData(**normalize(d5))
print("T5 OK:", r5.work[0].tasks)

# T6: 空 dict
r6 = ResumeData(**normalize({}))
print("T6 OK: empty dict, language =", r6.language)

# T7: age 为字符串（Pydantic v2 不自动转 int 时应报错——需验证）
d7 = {"name": "钱七", "age": "30", "education": [], "work": [], "project": []}
try:
    r7 = ResumeData(**normalize(d7))
    print("T7 OK: age str ->", r7.age)
except Exception as e:
    print("T7 FAIL(age str):", type(e).__name__, str(e)[:120])

# T8: tech_skills 为 list（field_validator 转 str）
d8 = {"name": "孙八", "tech_skills": ["Python", "Java"], "education": [], "work": [], "project": []}
r8 = ResumeData(**normalize(d8))
print("T8 OK: tech_skills ->", r8.tech_skills)

# T9: LLM 返回 list 类型（如 [{}]）
r9 = ResumeData(**normalize([{"name": "x"}]))
print("T9 OK: list input fallback, name =", r9.name)

print("ALL DONE")
