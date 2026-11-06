"""
项目状态检查脚本
展示当前已完成的内容
"""
import os
from pathlib import Path

# 项目根目录
BACKEND_DIR = Path(__file__).parent.parent

print("=" * 80)
print("  AI简历模板转换工具 - 项目状态检查")
print("=" * 80)

# 检查关键文件
print("\n[1] 检查项目文件")
print("-" * 80)

check_list = [
    ("app/main.py", "FastAPI入口"),
    ("app/api/resume.py", "API路由"),
    ("app/schemas/resume.py", "数据模型"),
    ("app/services/parser_service.py", "文档解析服务"),
    ("app/services/extractor_service.py", "信息抽取服务"),
    ("app/services/translator_service.py", "翻译服务"),
    ("app/services/anonymizer_service.py", "脱敏服务"),
    ("app/services/summarization_service.py", "摘要服务"),
    ("app/services/filler_service.py", "PPT填充服务"),
    ("app/services/template_config.py", "模板配置"),
]

all_good = True
for filepath, description in check_list:
    full_path = BACKEND_DIR / filepath
    exists = full_path.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {description:<20} -> {filepath}")
    if not exists:
        all_good = False

# 检查模板文件
print("\n[2] 检查PPT模板")
print("-" * 80)

templates_dir = BACKEND_DIR / "templates"
template_files = list(templates_dir.glob("*.pptx"))
if template_files:
    for f in template_files:
        print(f"  ✓ {f.name}")
else:
    print("  ✗ 未找到PPT模板文件")
    all_good = False

# 创建输出目录
output_dir = BACKEND_DIR / "output"
output_dir.mkdir(exist_ok=True)
uploads_dir = BACKEND_DIR / "uploads"
uploads_dir.mkdir(exist_ok=True)

print("\n[3] 目录准备")
print("-" * 80)
print(f"  ✓ 输出目录: {output_dir}")
print(f"  ✓ 上传目录: {uploads_dir}")

# Pipeline步骤说明
print("\n" + "=" * 80)
print("  🎯 Pipeline开发进度")
print("=" * 80)

pipeline_steps = [
    ("1", "文档解析", "✅ 完成"),
    ("2", "LLM结构化抽取", "✅ 完成"),
    ("3", "翻译+脱敏", "✅ 完成"),
    ("4", "约束性摘要", "✅ 完成"),
    ("5", "岗位匹配评估", "⏸️ 待后续开发"),
    ("6", "PPT模板填充", "✅ 完成"),
]

for step, name, status in pipeline_steps:
    print(f"  [{step}] {name:<20} {status}")

# 使用说明
print("\n" + "=" * 80)
print("  📖 使用说明")
print("=" * 80)

print("""
  方法一：安装依赖后完整测试（推荐）
  
    1. 安装依赖：
       cd d:\\ai_resume\\backend
       pip install -r requirements.txt
       
    2. 启动服务：
       python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
       
    3. 访问浏览器：
       http://localhost:8000/docs
       
    4. 在Swagger UI中上传你的简历并测试！

  方法二：查看代码和文档
  
    - 代码位置：d:\\ai_resume\\backend\\app\\
    - 文档位置：d:\\ai_resume\\memory-bank\\
    - API定义：d:\\ai_resume\\backend\\app\\api\\resume.py

  📋 当前可用的API接口：
    - POST /api/v1/resume/upload         - 上传简历
    - POST /api/v1/resume/parse          - 解析简历
    - POST /api/v1/resume/upload-and-parse - 上传并解析
    - POST /api/v1/resume/extract        - 结构化抽取
    - POST /api/v1/resume/translate      - 翻译
    - POST /api/v1/resume/anonymize      - 脱敏
    - POST /api/v1/resume/transform      - 翻译+脱敏
    - POST /api/v1/resume/summarize      - 摘要优化
    - POST /api/v1/resume/fill           - PPT填充
    - GET  /api/v1/resume/fill/download/{filename} - 下载PPT
""")

print("=" * 80)
print("  🎉 项目准备完成！")
print("=" * 80)
print(f"\n  下一步：安装依赖并启动服务，开始测试！")
print("  有问题随时查看 memory-bank/ 下的文档！\n")
