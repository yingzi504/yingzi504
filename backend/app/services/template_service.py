"""模板管理服务 — 步骤4.5

提供模板的增删改操作，数据存储于 SQLite + 本地 templates/ 目录。
"""
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.template import Template
from app.schemas.template import TemplateResponse


class TemplateService:
    """模板 CRUD 服务"""

    TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

    @staticmethod
    def _to_response(t: Template) -> TemplateResponse:
        """ORM → Pydantic 响应"""
        return TemplateResponse(
            id=str(t.id),
            name=t.name,
            category=t.category,
            version=t.version,
            updateTime=t.updated_at.strftime("%Y-%m-%d %H:%M") if t.updated_at else "",
            filePath=t.file_path,
            status=t.status,
        )

    @staticmethod
    def list_all(db: Session) -> List[TemplateResponse]:
        """获取全部模板"""
        rows = db.query(Template).order_by(Template.updated_at.desc()).all()
        return [TemplateService._to_response(r) for r in rows]

    @staticmethod
    def get_by_id(db: Session, template_id: int) -> Optional[TemplateResponse]:
        """获取单个模板"""
        t = db.query(Template).filter(Template.id == template_id).first()
        return TemplateService._to_response(t) if t else None

    @staticmethod
    def upload(db: Session, file_bytes: bytes, filename: str, name: str, category: str) -> TemplateResponse:
        """上传并保存模板文件"""
        TemplateService.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        ext = Path(filename).suffix or ".pptx"
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        dest_path = TemplateService.TEMPLATES_DIR / unique_name

        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        t = Template(
            name=name or filename,
            category=category or "vertical",
            version="1.0",
            file_path=str(dest_path),
            status="active",
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return TemplateService._to_response(t)

    @staticmethod
    def delete(db: Session, template_id: int) -> bool:
        """删除模板（数据库记录 + 文件）"""
        t = db.query(Template).filter(Template.id == template_id).first()
        if not t:
            return False
        # 删除文件
        if t.file_path and os.path.exists(t.file_path):
            os.remove(t.file_path)
        db.delete(t)
        db.commit()
        return True

    @staticmethod
    def set_active(db: Session, template_id: int, active: bool) -> Optional[TemplateResponse]:
        """启用/禁用模板"""
        t = db.query(Template).filter(Template.id == template_id).first()
        if not t:
            return None
        t.status = "active" if active else "inactive"
        t.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(t)
        return TemplateService._to_response(t)

    @staticmethod
    def upgrade(db: Session, template_id: int, file_bytes: bytes, filename: str) -> Optional[TemplateResponse]:
        """更新模板版本（上传新 .pptx 文件并自增版本号）"""
        t = db.query(Template).filter(Template.id == template_id).first()
        if not t:
            return None

        TemplateService.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

        # 自增版本号
        try:
            major, minor = t.version.split(".")
            new_version = f"{major}.{int(minor) + 1}"
        except (ValueError, AttributeError):
            new_version = "1.1"

        # 保存新文件
        ext = Path(filename).suffix or ".pptx"
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        dest_path = TemplateService.TEMPLATES_DIR / unique_name

        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        # 更新记录
        t.file_path = str(dest_path)
        t.version = new_version
        t.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(t)
        return TemplateService._to_response(t)
