"""模板管理 API — 步骤4.5 补全 CRUD 端点"""
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.template import TemplateResponse, TemplateUpdateRequest
from app.services.template_service import TemplateService

router = APIRouter()


def _now():
    return datetime.utcnow().isoformat()


def _ok(data=None, message: str = "", total: int = 0, page: int = 1, pageSize: int = 10):
    """构造标准 ApiResponse / ApiListResponse"""
    body = {"success": True, "message": message, "timestamp": _now()}
    if isinstance(data, list):
        body["data"] = data
        body["total"] = total
        body["page"] = page
        body["pageSize"] = pageSize
    else:
        body["data"] = data
    return body


def _err(code: str, msg: str):
    return {"success": False, "errorCode": code, "message": msg, "timestamp": _now()}


@router.get("/list")
async def list_templates(db: Session = Depends(get_db)):
    """获取全部模板列表（DB 驱动）"""
    templates = TemplateService.list_all(db)
    return _ok(data=templates, total=len(templates))


@router.get("/{template_id}")
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """获取单个模板"""
    t = TemplateService.get_by_id(db, template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    return _ok(data=t)


@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(""),
    category: str = Form("vertical"),
    db: Session = Depends(get_db),
):
    """上传模板文件"""
    if not file.filename or not file.filename.endswith(".pptx"):
        raise HTTPException(400, "仅支持 .pptx 模板文件")
    file_bytes = await file.read()
    t = TemplateService.upload(db, file_bytes, file.filename, name, category)
    return _ok(data=t, message="模板上传成功")


@router.delete("/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    """删除模板"""
    ok = TemplateService.delete(db, template_id)
    if not ok:
        raise HTTPException(404, "模板不存在")
    return _ok(message="模板已删除")


@router.put("/{template_id}")
async def upgrade_template(
    template_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """更新模板版本（上传新版 .pptx）"""
    if not file.filename or not file.filename.endswith(".pptx"):
        raise HTTPException(400, "仅支持 .pptx 模板文件")
    file_bytes = await file.read()
    t = TemplateService.upgrade(db, template_id, file_bytes, file.filename)
    if not t:
        raise HTTPException(404, "模板不存在")
    return _ok(data=t, message="模板版本更新成功")


@router.put("/{template_id}/status")
async def set_template_status(template_id: int, body: dict, db: Session = Depends(get_db)):
    """启用或禁用模板"""
    active = body.get("active", True)
    t = TemplateService.set_active(db, template_id, active)
    if not t:
        raise HTTPException(404, "模板不存在")
    return _ok(data=t, message="状态已更新")
