"""JD 管理服务 — 步骤4.5

提供岗位描述的增删改查操作。
"""
import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.jd import JD
from app.schemas.jd import JDResponse, JDCreateRequest, JDUpdateRequest


class JDService:
    """JD CRUD 服务"""

    @staticmethod
    def _to_response(j: JD) -> JDResponse:
        try:
            tags = json.loads(j.tags_json or "[]")
        except (TypeError, ValueError):
            tags = []
        try:
            structured_data = json.loads(j.structured_data) if j.structured_data else None
        except (TypeError, ValueError):
            structured_data = None
        created_at = j.created_at.strftime("%Y-%m-%d %H:%M") if j.created_at else ""
        updated_at = j.updated_at.strftime("%Y-%m-%d %H:%M") if j.updated_at else ""
        return JDResponse(
            id=str(j.id),
            title=j.title,
            position=j.title,
            department=j.department or "",
            category=j.category,
            language=j.language,
            isHot=j.is_hot,
            description=j.description or "",
            content=j.description or "",
            tags=tags,
            active=j.active is not False,
            structuredData=structured_data,
            createTime=created_at,
            usageCount=j.usage_count or 0,
            lastUsed=j.last_used.strftime("%Y-%m-%d %H:%M") if j.last_used else "",
            updatedAt=updated_at or created_at,
        )

    @staticmethod
    def list_all(db: Session, category: Optional[str] = None) -> List[JDResponse]:
        """获取 JD 列表，支持按分类筛选"""
        q = db.query(JD)
        if category:
            q = q.filter(JD.category == category)
        rows = q.order_by(JD.updated_at.desc()).all()
        return [JDService._to_response(r) for r in rows]

    @staticmethod
    def get_by_id(db: Session, jd_id: int) -> Optional[JDResponse]:
        j = db.query(JD).filter(JD.id == jd_id).first()
        return JDService._to_response(j) if j else None

    @staticmethod
    def create(db: Session, req: JDCreateRequest) -> JDResponse:
        j = JD(
            title=req.title,
            department=req.department,
            category=req.category,
            language=req.language,
            description=req.description,
            tags_json=json.dumps(req.tags, ensure_ascii=False),
            active=req.active,
            is_hot=req.is_hot,
        )
        db.add(j)
        db.commit()
        db.refresh(j)
        return JDService._to_response(j)

    @staticmethod
    def update(db: Session, jd_id: int, req: JDUpdateRequest) -> Optional[JDResponse]:
        j = db.query(JD).filter(JD.id == jd_id).first()
        if not j:
            return None
        update_data = req.model_dump(exclude_unset=True)
        # 前端可能传 is_hot 而非 isHot
        if "isHot" in update_data:
            update_data["is_hot"] = update_data.pop("isHot")
        if "tags" in update_data:
            update_data["tags_json"] = json.dumps(update_data.pop("tags") or [], ensure_ascii=False)
        for key, value in update_data.items():
            setattr(j, key, value)
        j.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(j)
        return JDService._to_response(j)

    @staticmethod
    def delete(db: Session, jd_id: int) -> bool:
        j = db.query(JD).filter(JD.id == jd_id).first()
        if not j:
            return False
        db.delete(j)
        db.commit()
        return True

    @staticmethod
    def increment_usage(db: Session, jd_id: int) -> None:
        """使用计数 +1"""
        j = db.query(JD).filter(JD.id == jd_id).first()
        if j:
            j.usage_count = (j.usage_count or 0) + 1
            j.last_used = datetime.utcnow()
            db.commit()

    @staticmethod
    def save_final_conversion(db: Session, task) -> JDResponse:
        content = task.content
        language = task.request.output_language
        title = content.title_en or content.title_cn
        if language == "CN":
            title = content.title_cn or content.title_en
        elif language == "CNEN" and content.title_cn and content.title_en:
            title = f"{content.title_cn} / {content.title_en}"

        structured = content.model_dump()
        description = json.dumps(structured, ensure_ascii=False)
        item = db.query(JD).filter(JD.source_task_id == task.task_id).first()
        if item is None:
            item = JD(source_task_id=task.task_id)
            db.add(item)

        item.title = title
        item.department = content.department
        item.category = content.category
        item.language = language
        item.description = description
        item.structured_data = description
        item.tags_json = "[]"
        item.active = True
        item.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(item)
        return JDService._to_response(item)
