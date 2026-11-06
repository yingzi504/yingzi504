"""
处理任务数据模型 - Pipeline 步骤 2.10

用于跟踪简历处理 Pipeline 的异步任务状态
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON
from app.models.database import Base


class ProcessingTask(Base):
    """处理任务表"""
    __tablename__ = "processing_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), default="pending", index=True)  # pending/processing/completed/failed
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(50), default="")  # 当前步骤名称
    step_index = Column(Integer, default=0)  # 当前步骤序号 0-6

    # 输入参数
    file_id = Column(String(36), nullable=False)
    template_type = Column(String(20), default="vertical")  # vertical/horizontal
    target_language = Column(String(5), default="EN")
    job_position = Column(String(100), default="")
    template_language = Column(String(5), default="")

    # 中间结果
    resume_data = Column(JSON, nullable=True)  # 当前步骤产出的 ResumeData
    raw_text = Column(Text, nullable=True)  # 原始解析文本

    # 最终输出
    output_path = Column(String(500), nullable=True)
    output_filename = Column(String(200), nullable=True)
    error_message = Column(Text, nullable=True)

    # 时间统计
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # 步骤4.8: 时间排序索引
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # 各步骤耗时 (秒)
    step_durations = Column(JSON, nullable=True, default=dict)
    total_duration = Column(Float, nullable=True)

    def to_dict(self) -> dict:
        """转换为字典，用于API响应"""
        return {
            "task_id": self.id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "file_id": self.file_id,
            "template_type": self.template_type,
            "target_language": self.target_language,
            "job_position": self.job_position,
            "output_filename": self.output_filename,
            "error_message": self.error_message,
            "step_durations": self.step_durations or {},
            "total_duration": self.total_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
