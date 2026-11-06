#!/usr/bin/env python3
"""
AI Resume Converter - 启动脚本
用于安全启动FastAPI服务
"""
import sys
import os

from app.core.console import configure_console_output

# ── Windows 控制台编码修复 ──
# Windows 下 stdout 默认 GBK(cp936)，print 含 emoji 时抛 UnicodeEncodeError，
# 且该异常继承自 ValueError，会被 API 层误捕获返回 400。强制兜底避免崩溃。
configure_console_output()

# 确保能导入app模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# import ssl
# import os

# # 关闭SSL证书校验
# ssl._create_default_https_context = ssl._create_unverified_context
# os.environ["CURL_CA_BUNDLE"] = ""
# os.environ["REQUESTS_CA_BUNDLE"] = ""
# os.environ["SSL_CERT_FILE"] = ""

print("=" * 80)
print("  AI Resume Converter - Starting Server")
print("=" * 80)
print()

# 尝试导入应用
try:
    from app.main import app
    print("[1] OK - Application imported successfully")
except Exception as e:
    print(f"[1] ERROR - Failed to import app: {e}")
    print("\nPlease install dependencies first:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

# 检查基本导入
try:
    import fastapi
    import uvicorn
    from pydantic import BaseModel
    print("[2] OK - Core dependencies loaded")
except Exception as e:
    print(f"[2] WARNING - Some dependencies missing: {e}")
    print("    Continuing anyway...")

print()
print("=" * 80)
print("  Server will start at: http://localhost:8000")
print("  Swagger UI: http://localhost:8000/docs")
print("=" * 80)
print()

# 启动服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
