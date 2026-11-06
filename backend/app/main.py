from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import (
    configured_cors_origins,
    private_network_origin_regex,
    settings,
)
from app.core.logging_config import configure_application_logging

configure_application_logging(debug=settings.debug)

from app.api import router as api_router, create_versioned_router
import app.models  # 确保所有模型表在启动时创建

app = FastAPI(
    title="AI Resume Converter API",
    description="AI驱动的简历模板转化工具",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_cors_origins(),
    allow_origin_regex=private_network_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 — 当前版本 v1
# 未来新增 v2: app.include_router(create_versioned_router("v2"), prefix="/api/v2")
from app.api.access import router as access_router, access_middleware
from app.services.access_service import import_legacy_outputs

app.middleware("http")(access_middleware)
app.include_router(access_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
def initialize_access_archive():
    import_legacy_outputs()



@app.get("/")
async def root():
    return {
        "message": "AI Resume Converter API",
        "version": "1.0.0",
        "api_version": settings.api_version,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """非版本化的健康检查端点"""
    return {"status": "healthy", "api_version": settings.api_version}


# ============================================================
# 版本发现端点（步骤4.7 新增）
# ============================================================
@app.get("/api/version")
async def api_version_info():
    """返回当前 API 版本信息，用于前端版本发现"""
    return {
        "current_version": settings.api_version,
        "version_int": settings.api_version_int,
        "deprecated_versions": [
            v.strip() for v in settings.deprecated_versions.split(",") if v.strip()
        ] if settings.deprecated_versions else [],
        "all_versions": {
            "v1": "/api/v1",
        },
        "message": "始终使用最新版本。已废弃版本将在下一大版本中移除。",
    }
