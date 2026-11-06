"""模板 Model — 步骤4.5"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from app.models.database import Base


class Template(Base):
    """PPT 模板"""
    __tablename__ = "templates"
    __table_args__ = (
        Index('idx_template_status_updated', 'status', 'updated_at'),  # 步骤4.8: 状态+时间排序
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="模板名称")
    category = Column(String(20), nullable=False, default="vertical", comment="分类: vertical(纵向) / horizontal(横向)")
    version = Column(String(20), default="1.0", comment="版本号")
    file_path = Column(String(500), nullable=False, comment="模板文件存储路径")
    status = Column(String(20), default="active", index=True, comment="状态: active / inactive")  # 步骤4.8: 状态索引
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)  # 步骤4.8: 排序索引
