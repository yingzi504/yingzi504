"""Cookie sessions, API authorization and administrator reporting."""
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.core.config import is_allowed_browser_origin, settings
from app.core.cv_rules import cv_download_filename
from app.core.jd_dictionaries import DEPARTMENT_CODES
from app.models.database import SessionLocal
from app.models.access import User, LoginSession, AuditEvent, Resource
from app.services.access_service import (
    FEATURES, audit, create_user, current_actor, normalize_email, owned_resource,
    password_hash, password_matches, public_user, resource_data,
)

COOKIE = "resume_session"
router = APIRouter()
dummy_hash = password_hash(secrets.token_urlsafe(32))


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def require_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "请先登录")
    return user


def require_admin(request: Request):
    user = require_user(request)
    if user["must_change_password"]:
        raise HTTPException(403, "请先修改初始密码")
    if user["role"] != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


async def authorize_business(request: Request):
    user = require_user(request)
    if user["must_change_password"]:
        raise HTTPException(403, "请先修改初始密码")
    path = request.url.path.removeprefix("/api/v1")
    feature = None
    if path.startswith("/process"):
        feature = "cv"
    elif path.startswith("/jd-conversion"):
        feature = "jd"
    elif path.startswith("/jd"):
        feature = "library"
    elif path.startswith("/template"):
        feature = "templates" if request.method != "GET" else None
    elif path.startswith("/termbase"):
        feature = "terminology"
    elif path == "/resume/upload":
        if user["role"] != "admin" and not ({"cv", "jd"} & set(user["permissions"])):
            raise HTTPException(403, "此账号没有上传权限")
    elif path.startswith("/resume"):
        # Legacy diagnostic endpoints accept raw text/paths and are admin-only.
        if user["role"] != "admin":
            raise HTTPException(403, "此接口仅供管理员使用")
    if feature and user["role"] != "admin" and feature not in user["permissions"]:
        raise HTTPException(403, "此账号未开通该功能")
    if path.startswith("/jd-conversion/") and path.endswith("/save") and user["role"] != "admin" and "library" not in user["permissions"]:
        raise HTTPException(403, "此账号未开通 JD 库功能")
    task_id = request.path_params.get("task_id")
    if task_id:
        owned_resource(task_id, user)
    if request.method in {"POST", "PUT"} and "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
        except ValueError:
            return
        if isinstance(body, dict) and body.get("file_id"):
            item = owned_resource(body["file_id"], user)
            if item.kind != "upload":
                raise HTTPException(422, "文件标识无效")


async def access_middleware(request: Request, call_next):
    request.state.user = None
    cookie = request.cookies.get(COOKIE)
    if cookie:
        with SessionLocal() as db:
            session = db.get(LoginSession, token_digest(cookie))
            if session and session.expires_at > datetime.utcnow():
                user = db.get(User, session.user_id)
                if user and user.active:
                    request.state.user = public_user(user)
    context_token = current_actor.set(request.state.user)
    code = 500
    try:
        if request.url.path.startswith("/api/v1/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if not is_allowed_browser_origin(origin, str(request.base_url)):
                code = 403
                return JSONResponse({"detail": "不允许来自此站点的请求"}, status_code=403)
        response = await call_next(request)
        code = response.status_code
        return response
    finally:
        if request.url.path.startswith("/api/v1/") and request.method != "OPTIONS":
            route = request.scope.get("route")
            action = f"{request.method} {getattr(route, 'path', '/api/v1/unknown')}"
            params = request.path_params
            resource_id = next((str(params[k]) for k in ("task_id", "resource_id", "user_id", "history_id", "jd_id", "template_id", "file_id", "filename") if k in params), None)
            audit(action, code, resource_id, getattr(request.state, "user", None),
                  request.client.host if request.client else None)
        current_actor.reset(context_token)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
def login(body: LoginRequest, request: Request, response: Response):
    email = normalize_email(body.email)
    ip = request.client.host if request.client else "unknown"
    with SessionLocal() as db:
        failures = db.query(AuditEvent).filter(
            AuditEvent.action == "auth.login.failed", AuditEvent.ip_address == ip,
            AuditEvent.created_at > datetime.utcnow() - timedelta(minutes=15)).count()
        if failures >= 10:
            raise HTTPException(429, "登录尝试过多，请在 15 分钟后重试")
        user = db.query(User).filter_by(email=email).first()
        if user is None and secrets.compare_digest(body.password.encode(), b"123456"):
            try:
                user = create_user(db, email, role="member", must_change_password=False)
                audit("auth.account.created", resource_id=str(user.id), actor={"id": user.id}, ip=ip)
            except (IntegrityError, HTTPException) as exc:
                # Concurrent first logins resolve to the existing account, without resetting it.
                db.rollback()
                if isinstance(exc, HTTPException) and exc.status_code != 409:
                    raise
                user = db.query(User).filter_by(email=email).first()
        valid = password_matches(body.password, user.password_hash if user else dummy_hash)
        if not user or not valid or not user.active:
            audit("auth.login.failed", 401, actor={"id": user.id} if user else None, ip=ip)
            raise HTTPException(401, "账号或密码错误，或账号已停用")
        token = secrets.token_urlsafe(48)
        # Rotate an existing browser session when signing in again.
        old = request.cookies.get(COOKIE)
        if old:
            db.query(LoginSession).filter_by(token_hash=token_digest(old)).delete()
        db.query(LoginSession).filter(LoginSession.expires_at <= datetime.utcnow()).delete()
        db.add(LoginSession(token_hash=token_digest(token), user_id=user.id,
                            expires_at=datetime.utcnow() + timedelta(hours=8)))
        user.last_login_at = datetime.utcnow()
        db.commit()
        result = public_user(user)
        request.state.user = result
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=28800,
                        secure=settings.environment.lower() == "production", path="/")
    return {"success": True, "data": result}


@router.get("/auth/me")
def me(user=Depends(require_user)):
    return {"success": True, "data": user}


@router.post("/auth/logout")
def logout(request: Request, response: Response, user=Depends(require_user)):
    with SessionLocal() as db:
        db.query(LoginSession).filter_by(token_hash=token_digest(request.cookies.get(COOKIE, ""))).delete()
        db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"success": True}


class PasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


@router.post("/auth/password")
def change_password(body: PasswordRequest, request: Request, user=Depends(require_user)):
    with SessionLocal() as db:
        row = db.get(User, user["id"])
        if not password_matches(body.current_password, row.password_hash):
            raise HTTPException(400, "当前密码错误")
        if body.new_password == body.current_password or body.new_password.strip() == "123456":
            raise HTTPException(422, "新密码不能与当前密码相同")
        row.password_hash = password_hash(body.new_password)
        row.must_change_password = False
        # Keep only the current session; revoke other devices.
        db.query(LoginSession).filter(LoginSession.user_id == row.id,
            LoginSession.token_hash != token_digest(request.cookies.get(COOKIE, ""))).delete()
        db.commit()
        return {"success": True, "data": public_user(row)}


class NewUser(BaseModel):
    email: str = Field(max_length=254)
    role: Literal["admin", "member"] = "member"
    account_type: str = Field(default="standard", min_length=1, max_length=50)
    permissions: list[Literal["cv", "jd", "library", "templates", "terminology"]] = Field(default_factory=lambda: sorted(FEATURES))


class UpdateUser(BaseModel):
    active: bool
    account_type: str = Field(min_length=1, max_length=50)
    permissions: list[Literal["cv", "jd", "library", "templates", "terminology"]]


@router.post("/admin/users")
def add_user(body: NewUser, admin=Depends(require_admin)):
    with SessionLocal() as db:
        try:
            user = create_user(db, body.email, body.role, body.account_type, body.permissions)
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "此邮箱已存在")
        audit("admin.user.created", resource_id=str(user.id), actor=admin)
        return {"success": True, "data": public_user(user)}


@router.get("/admin/users")
def users(page: int = Query(1, ge=1), search: str = Query("", max_length=254), admin=Depends(require_admin)):
    with SessionLocal() as db:
        q = db.query(User).filter(User.email.contains(search, autoescape=True))
        total = q.count()
        rows = q.order_by(User.id.desc()).offset((page-1)*20).limit(20).all()
        ids = [row.id for row in rows]
        counts = dict(db.query(Resource.owner_id, func.count(Resource.id)).filter(
            Resource.owner_id.in_(ids), Resource.kind.in_(["cv", "jd"])).group_by(Resource.owner_id).all())
        operations = dict(db.query(AuditEvent.user_id, func.count(AuditEvent.id)).filter(
            AuditEvent.user_id.in_(ids)).group_by(AuditEvent.user_id).all())
        return {"success": True, "total": total, "data": [dict(public_user(row), task_count=counts.get(row.id, 0),
                operation_count=operations.get(row.id, 0)) for row in rows]}


@router.put("/admin/users/{user_id}")
def edit_user(user_id: int, body: UpdateUser, admin=Depends(require_admin)):
    with SessionLocal() as db:
        row = db.get(User, user_id)
        if not row:
            raise HTTPException(404, "账号不存在")
        if row.role == "admin" and not body.active:
            raise HTTPException(400, "不可停用管理员账号")
        row.active, row.account_type = body.active, body.account_type
        row.permissions = json.dumps(body.permissions)
        if not row.active:
            db.query(LoginSession).filter_by(user_id=row.id).delete()
        db.commit()
        return {"success": True, "data": public_user(row)}


@router.post("/admin/users/{user_id}/reset-password")
def reset_password(user_id: int, admin=Depends(require_admin)):
    with SessionLocal() as db:
        row = db.get(User, user_id)
        if not row:
            raise HTTPException(404, "账号不存在")
        row.password_hash, row.must_change_password = password_hash("123456"), True
        db.query(LoginSession).filter_by(user_id=row.id).delete()
        db.commit()
    return {"success": True}


@router.get("/admin/statistics")
def statistics(admin=Depends(require_admin)):
    with SessionLocal() as db:
        return {"success": True, "data": {
            "users": db.query(User).count(), "active_users": db.query(User).filter_by(active=True).count(),
            "tasks": db.query(Resource).filter(Resource.kind.in_(["cv", "jd"])).count(),
            "completed": db.query(Resource).filter(Resource.kind.in_(["cv", "jd"]), Resource.status == "completed").count(),
            "operations": db.query(AuditEvent).count()}}


@router.get("/admin/audit")
def events(page: int = Query(1, ge=1), user_id: int | None = None,
           action: str = Query("", max_length=120), admin=Depends(require_admin)):
    with SessionLocal() as db:
        q = db.query(AuditEvent, User.email).outerjoin(User, User.id == AuditEvent.user_id)
        if user_id is not None:
            q = q.filter(AuditEvent.user_id == user_id)
        if action:
            q = q.filter(AuditEvent.action.contains(action, autoescape=True))
        total = q.count()
        rows = q.order_by(AuditEvent.id.desc()).offset((page-1)*30).limit(30).all()
        return {"success": True, "total": total, "data": [{"id": e.id, "email": email,
                "action": e.action, "resource_id": e.resource_id, "status_code": e.status_code,
                "ip_address": e.ip_address, "created_at": e.created_at.isoformat()} for e, email in rows]}


def ready_user(request: Request):
    user = require_user(request)
    if user["must_change_password"]:
        raise HTTPException(403, "请先修改初始密码")
    return user


@router.get("/records")
def records(page: int = Query(1, ge=1), user_id: int | None = None,
            status: str = Query("", max_length=30), user=Depends(ready_user)):
    with SessionLocal() as db:
        q = db.query(Resource, User.email).outerjoin(User, User.id == Resource.owner_id).filter(Resource.kind != "upload")
        if user["role"] != "admin":
            q = q.filter(Resource.owner_id == user["id"])
        elif user_id is not None:
            q = q.filter(Resource.owner_id == user_id)
        if status:
            q = q.filter(Resource.status == status)
        total = q.count()
        rows = q.order_by(Resource.created_at.desc()).offset((page-1)*20).limit(20).all()
        return {"success": True, "total": total, "data": [dict(resource_data(r), email=email) for r, email in rows]}


@router.get("/cv-library")
def cv_library(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department: str = Query("", max_length=50),
    position: str = Query("", max_length=200),
    user=Depends(ready_user),
):
    """List completed CV archives, classified by the selected department."""
    if user["role"] != "admin" and "cv" not in user["permissions"]:
        raise HTTPException(403, "此账号未开通 CV 功能")
    with SessionLocal() as db:
        base = db.query(Resource).filter(
            Resource.kind == "cv", Resource.status == "completed"
        )
        if user["role"] != "admin":
            base = base.filter(Resource.owner_id == user["id"])

        counts = dict(
            base.with_entities(Resource.department, func.count(Resource.id))
            .group_by(Resource.department)
            .all()
        )
        query = base
        if department == "__unclassified__":
            query = query.filter(Resource.department == "")
        elif department:
            if department not in DEPARTMENT_CODES:
                raise HTTPException(422, "部门不在固定目录中")
            query = query.filter(Resource.department == department)
        if position.strip():
            query = query.filter(Resource.position.ilike(f"%{position.strip()}%"))

        total = query.count()
        rows = (
            query.order_by(Resource.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        departments = [
            {"code": code, "count": counts.get(code, 0)} for code in DEPARTMENT_CODES
        ]
        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "departments": departments,
            "unclassified": counts.get("", 0),
            "data": [resource_data(row) for row in rows],
        }


@router.get("/records/{resource_id}")
def record_detail(resource_id: str, user=Depends(ready_user)):
    item = owned_resource(resource_id, user)
    return {"success": True, "data": dict(resource_data(item), metadata=json.loads(item.snapshot))}


@router.get("/records/{resource_id}/download")
def download_record(resource_id: str, format: Literal["pptx", "pdf", "docx"], user=Depends(ready_user)):
    item = owned_resource(resource_id, user)
    files = json.loads(item.files)
    value = files.get(format)
    # Older CV records may contain only PPTX even when PDF conversion is
    # available. Generate it on demand beside the archived PPTX and persist
    # the path so subsequent downloads are ordinary file responses.
    if format == "pdf" and item.kind == "cv" and not value:
        pptx_value = files.get("pptx")
        if pptx_value and Path(pptx_value).is_file():
            try:
                from app.services.pdf_converter import PdfConverterService
                value = PdfConverterService.ensure_pdf_for_pptx(
                    pptx_value, str(Path(pptx_value).parent)
                )
                with SessionLocal() as db:
                    current = db.get(Resource, item.id)
                    persisted = json.loads(current.files)
                    persisted["pdf"] = str(Path(value).resolve())
                    current.files = json.dumps(persisted)
                    db.commit()
            except Exception as exc:
                raise HTTPException(404, f"PDF 文件尚未生成，请检查 PDF 转换环境: {exc}") from exc
    if not value or item.kind == "upload":
        raise HTTPException(404, "此格式的文件不可用")
    path = Path(value).resolve()
    if not path.is_relative_to(settings.output_path.resolve()) or not path.is_file():
        raise HTTPException(404, "文件不存在")
    return FileResponse(
        path,
        filename=cv_download_filename(path.name),
        headers={"Cache-Control": "no-store"},
    )
