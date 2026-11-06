"""JD Model — 步骤4.5"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index
from sqlalchemy.sql import func
from app.models.database import Base


class JD(Base):
    """岗位描述"""
    __tablename__ = "jds"
    __table_args__ = (
        Index('idx_jd_category_updated', 'category', 'updated_at'),  # 步骤4.8: 分类筛选+时间排序
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    department = Column(String(200), default="")
    tags_json = Column(Text, default="[]")
    structured_data = Column(Text, default="")
    active = Column(Boolean, default=True)
    source_task_id = Column(String(36), default="", index=True)
    title = Column(String(200), nullable=False, comment="JD 标题")
    category = Column(String(50), nullable=False, index=True, comment="分类: 汽车技术/产品管理/软件开发等")  # 步骤4.8: 分类索引
    language = Column(String(10), default="CN", comment="语言: CN / EN")
    description = Column(Text, default="", comment="JD 详细描述")
    is_hot = Column(Boolean, default=False, comment="是否热门标记")
    usage_count = Column(Integer, default=0, comment="使用次数")
    last_used = Column(DateTime(timezone=True), nullable=True, comment="最后使用时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)  # 步骤4.8: 排序索引
