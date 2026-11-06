#!/usr/bin/env python3
"""
AI Resume Converter - Server Startup Script
简单启动脚本
"""
import sys
import os

from app.core.console import configure_console_output

configure_console_output()

# ── 修复 Windows SSL 证书崩溃（必须在所有其他导入之前）──
# Python 3.13 + Windows 下，ssl.create_default_context() → load_default_certs()
# → _load_windows_store_certs() 加载系统证书存储时可能因损坏证书而崩溃:
#   [ASN1: NOT_ENOUGH_DATA] not enough data (_ssl.c:4192)
# aiohttp（litellm 的依赖）在模块导入时就执行 ssl.create_default_context()，
# 所以必须在任何第三方库导入前完成 monkey-patch。
import ssl
import certifi

# 1. 替换 Windows 证书存储加载为空操作（避免加载损坏证书）
_original_load_windows = ssl.SSLContext._load_windows_store_certs
def _patched_load_windows(self, storename, purpose):
    pass  # 跳过 Windows 证书存储，使用 certifi 的 CA bundle 代替
ssl.SSLContext._load_windows_store_certs = _patched_load_windows

# 2. 强制使用 certifi CA bundle
_cafile = certifi.where()
os.environ["SSL_CERT_FILE"] = _cafile
os.environ["REQUESTS_CA_BUNDLE"] = _cafile
os.environ["CURL_CA_BUNDLE"] = _cafile
print(f"[0] SSL: Windows cert store disabled, using certifi CA bundle: {_cafile}")

# 确保在正确的目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("  AI Resume Converter - Starting Server")
print("=" * 80)
print()

try:
    import uvicorn
    print("[1] OK - Uvicorn loaded")
    
    from app.main import app
    print("[2] OK - Application loaded")
    print(f"[3] OK - Title: {app.title}")
    print(f"[4] OK - Version: {app.version}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\nPlease check your installation.")
    sys.exit(1)

print()
print("=" * 80)
print("  Server is starting...")
print("  Access URLs:")
print("  - API Root: http://localhost:8000")
print("  - Swagger UI: http://localhost:8000/docs  <-- Use this to test!")
print("  - Health Check: http://localhost:8000/health")
print("=" * 80)
print()

if __name__ == "__main__":
    from app.core.config import settings
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="debug" if settings.debug else "info",
        access_log=True,
    )
