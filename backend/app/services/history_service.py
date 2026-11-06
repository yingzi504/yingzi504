"""历史记录服务 — 步骤4.5

提供处理历史的查询、删除和统计功能。
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.models.history import ProcessingHistory
from app.services.access_service import visible_task_ids
from app.models.task import ProcessingTask
from app.schemas.history import HistoryItemResponse, StatisticsResponse
from app.core.cache import statistics_cache  # 步骤4.8: TTL 缓存


class HistoryService:
    """历史记录查询服务"""

    @staticmethod
    def _to_response(h: ProcessingHistory) -> HistoryItemResponse:
        return HistoryItemResponse(
            id=str(h.id),
            timestamp=h.created_at.strftime("%Y-%m-%d %H:%M") if h.created_at else "",
            originalFile=h.original_file or "",
            fileSize="",  # 历史表中无此字段
            jobPosition=h.job_position or "",
            language=h.language or "CN",
            template="",  # 历史表中无此字段
            jdMatchScore=None,
            status=h.status or "completed",
            processingTime="",  # 可在后续补全
            outputFile=h.output_file or "",
        )

    @staticmethod
    def list_all(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
    ) -> tuple:
        """分页查询历史记录"""
        q = db.query(ProcessingHistory).filter(ProcessingHistory.task_id.in_(visible_task_ids()))
        if status:
            q = q.filter(ProcessingHistory.status == status)
        total = q.count()
        rows = q.order_by(ProcessingHistory.created_at.desc()) \
                 .offset((page - 1) * page_size) \
                 .limit(page_size).all()
        items = [HistoryService._to_response(r) for r in rows]
        return items, total

    @staticmethod
    def get_by_id(db: Session, history_id: int) -> Optional[HistoryItemResponse]:
        h = db.query(ProcessingHistory).filter(ProcessingHistory.id == history_id, ProcessingHistory.task_id.in_(visible_task_ids())).first()
        return HistoryService._to_response(h) if h else None

    @staticmethod
    def delete(db: Session, history_id: int) -> bool:
        h = db.query(ProcessingHistory).filter(ProcessingHistory.id == history_id, ProcessingHistory.task_id.in_(visible_task_ids())).first()
        if not h:
            return False
        db.delete(h)
        db.commit()
        return True

    @staticmethod
    def get_statistics(db: Session) -> StatisticsResponse:
        """获取统计数据（步骤4.8: 3合1查询 + TTL缓存）"""
        # 尝试从缓存读取
        cached = None
        if cached is not None:
            return cached

        # 单次查询完成全部统计：总数、成功数、本月数
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stats = db.query(
            func.count(ProcessingHistory.id).label("total"),
            func.sum(
                case((ProcessingHistory.status == "completed", 1), else_=0)
            ).label("succeeded"),
            func.sum(
                case((ProcessingHistory.created_at >= month_start, 1), else_=0)
            ).label("monthly"),
        ).filter(ProcessingHistory.task_id.in_(visible_task_ids())).first()

        total = stats.total or 0
        succeeded = stats.succeeded or 0
        monthly = stats.monthly or 0
        success_rate = round(succeeded / total * 100, 1) if total > 0 else 0.0

        result = StatisticsResponse(total=total, successRate=success_rate, monthly=monthly)

        # 写入缓存（3分钟 TTL）
        # Statistics are scoped per user; do not share a global cache.
        return result
