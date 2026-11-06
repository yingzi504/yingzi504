from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from app.models.database import Base


class ProcessingHistory(Base):
    """处理历史记录"""
    __tablename__ = "processing_history"
    __table_args__ = (
        Index('idx_history_status_created', 'status', 'created_at'),  # 步骤4.8: 状态筛选+时间排序
    )
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    original_file = Column(String)
    job_position = Column(String, nullable=True)
    language = Column(String, default="CN")
    status = Column(String, default="pending", index=True)  # 步骤4.8: 状态索引
    output_file = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # 步骤4.8: 时间排序索引
    completed_at = Column(DateTime(timezone=True), nullable=True)
