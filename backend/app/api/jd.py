"""JD 管理 API — 步骤4.5 补全 CRUD 端点"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.jd import JDCreateRequest, JDUpdateRequest
from app.services.jd_service import JDService

router = APIRouter()


def _now():
    return datetime.utcnow().isoformat()


def _ok(data=None, message: str = "", total: int = 0, page: int = 1, pageSize: int = 10):
    body = {"success": True, "message": message, "timestamp": _now()}
    if isinstance(data, list):
        body["data"] = data
        body["total"] = total
        body["page"] = page
        body["pageSize"] = pageSize
    else:
        body["data"] = data
    return body


@router.get("/list")
async def list_jds(
    category: Optional[str] = Query(None, description="分类筛选"),
    db: Session = Depends(get_db),
):
    """获取 JD 列表"""
    items = JDService.list_all(db, category=category)
    return _ok(data=items, total=len(items))


@router.get("/{jd_id}")
async def get_jd(jd_id: int, db: Session = Depends(get_db)):
    """获取单个 JD"""
    j = JDService.get_by_id(db, jd_id)
    if not j:
        raise HTTPException(404, "JD不存在")
    return _ok(data=j)


@router.post("/create")
async def create_jd(req: JDCreateRequest, db: Session = Depends(get_db)):
    """创建 JD"""
    j = JDService.create(db, req)
    return _ok(data=j, message="JD创建成功")


@router.put("/{jd_id}")
async def update_jd(jd_id: int, req: JDUpdateRequest, db: Session = Depends(get_db)):
    """更新 JD"""
    j = JDService.update(db, jd_id, req)
    if not j:
        raise HTTPException(404, "JD不存在")
    return _ok(data=j, message="JD更新成功")


@router.delete("/{jd_id}")
async def delete_jd(jd_id: int, db: Session = Depends(get_db)):
    """删除 JD"""
    ok = JDService.delete(db, jd_id)
    if not ok:
        raise HTTPException(404, "JD不存在")
    return _ok(message="JD已删除")


@router.post("/match")
async def match_jd(req: dict):
    """JD 匹配（占位）"""
    return _ok(data={"score": 0}, message="JD匹配功能开发中")
