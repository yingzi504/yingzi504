"""历史记录 API — 步骤4.5 补全 CRUD 端点"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.history_service import HistoryService

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
async def list_history(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """分页查询历史记录"""
    items, total = HistoryService.list_all(db, page=page, page_size=pageSize, status=status)
    return _ok(data=items, total=total, page=page, pageSize=pageSize)


@router.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """获取统计信息"""
    stats = HistoryService.get_statistics(db)
    return _ok(data=stats)


@router.get("/{history_id}")
async def get_history(history_id: int, db: Session = Depends(get_db)):
    """获取单条历史"""
    h = HistoryService.get_by_id(db, history_id)
    if not h:
        raise HTTPException(404, "历史记录不存在")
    return _ok(data=h)


@router.delete("/{history_id}")
async def delete_history(history_id: int, db: Session = Depends(get_db)):
    """删除历史记录"""
    ok = HistoryService.delete(db, history_id)
    if not ok:
        raise HTTPException(404, "历史记录不存在")
    return _ok(message="历史记录已删除")
