"""API 路由注册 — 版本化策略（步骤4.7）

当前活跃版本: v1
路由前缀: /api/v1

版本化策略:
  - 所有业务 API 挂载在 /api/{version}/ 下
  - 新增 breaking change → 创建新版本路由（如 v2），旧版本保留至少一个大版本周期
  - 非业务端点（/health, /, /docs）不进行版本化
"""
from fastapi import APIRouter, Depends
from app.api.access import authorize_business

# ============================================================
# v1 路由定义（当前活跃版本）
# ============================================================
router = APIRouter(dependencies=[Depends(authorize_business)])

# 导入各模块路由
from app.api import resume, template, termbase, process, jd, history, jd_conversion

# 注册子路由
router.include_router(resume.router, prefix="/resume", tags=["resume"])
router.include_router(template.router, prefix="/template", tags=["template"])
router.include_router(termbase.router, prefix="/termbase", tags=["termbase"])
router.include_router(process.router, tags=["process"])
router.include_router(jd.router, prefix="/jd", tags=["jd"])
router.include_router(history.router, prefix="/history", tags=["history"])
router.include_router(jd_conversion.router, prefix="/jd-conversion", tags=["jd-conversion"])


# ============================================================
# 版本化路由工厂（为未来 v2+ 预留扩展点）
# ============================================================
def create_versioned_router(version: str) -> APIRouter:
    """创建指定版本的路由器。

    用法:
        v2_router = create_versioned_router("v2")
        app.include_router(v2_router, prefix="/api/v2")

    Args:
        version: API 版本号，如 "v1", "v2"

    Returns:
        包含对应版本所有子路由的 APIRouter
    """
    if version == "v1":
        # v1 直接返回当前活跃路由（已在上面定义）
        return router

    # v2+ 创建新的路由器
    new_router = APIRouter()

    # 新版本引入的模块在此注册
    # 示例:
    # from app.api.v2 import resume as resume_v2
    # new_router.include_router(resume_v2.router, prefix="/resume", tags=["resume-v2"])

    return new_router
