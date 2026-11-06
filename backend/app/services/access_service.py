"""Account security and durable conversion ownership. No resume text in audit logs."""
import hashlib
import hmac
import json
import re
import secrets
import shutil
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
from app.core.config import settings
from app.core.cv_rules import cv_download_filename
from app.models.database import SessionLocal
from app.models.access import User, AuditEvent, Resource

current_actor = ContextVar("current_actor", default=None)
FEATURES = {"cv", "jd", "library", "templates", "terminology"}


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def password_matches(password, encoded):
    try:
        _, rounds, salt, expected = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def normalize_email(email):
    email = email.strip().lower()
    if not email or len(email) > 254 or any(ord(char) < 32 for char in email):
        raise HTTPException(422, "请输入有效的账号名称（1 至 254 个字符）")
    return email


def public_user(user):
    return {"id": user.id, "email": user.email, "role": user.role,
            "account_type": user.account_type, "permissions": json.loads(user.permissions),
            "active": user.active, "must_change_password": user.must_change_password,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None}


def create_user(db, email, role="member", account_type="standard", permissions=None, must_change_password=True):
    email = normalize_email(email)
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "此账号已存在")
    user = User(email=email, password_hash=password_hash("123456"), role=role, must_change_password=must_change_password,
                account_type=account_type, permissions=json.dumps(sorted(FEATURES if permissions is None else permissions)))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def audit(action, status_code=200, resource_id=None, actor=None, ip=None):
    actor = actor or current_actor.get()
    with SessionLocal() as db:
        db.add(AuditEvent(user_id=actor["id"] if actor else None, action=action,
                          status_code=status_code, resource_id=resource_id, ip_address=ip))
        db.commit()


def register_resource(resource_id, kind, name="", files=None, department="", position=""):
    actor = current_actor.get()
    if not actor:  # Internal tools/tests do not create attributed user records.
        return
    with SessionLocal() as db:
        db.add(Resource(id=resource_id, owner_id=actor["id"], kind=kind, name=name,
                        department=department, position=position,
                        status="uploaded" if kind == "upload" else "pending", files=json.dumps(files or {})))
        db.commit()
    audit(f"{kind}.created", resource_id=resource_id)


def owned_resource(resource_id, actor=None):
    actor = actor or current_actor.get()
    with SessionLocal() as db:
        item = db.get(Resource, resource_id)
        if not item or not actor or (actor["role"] != "admin" and item.owner_id != actor["id"]):
            raise HTTPException(404, "记录不存在或无权访问")
        db.expunge(item)
        return item


def visible_task_ids():
    actor = current_actor.get()
    if not actor:
        return set()
    with SessionLocal() as db:
        q = db.query(Resource.id)
        if actor["role"] != "admin":
            q = q.filter(Resource.owner_id == actor["id"])
        return {row[0] for row in q.all()}


def persist_task(task, kind):
    """Archive under a task ID so identical generated names never overwrite history."""
    with SessionLocal() as db:
        record = db.get(Resource, task.task_id)
        if not record:
            return
        previous = record.status
        record.status = task.status
        record.updated_at = datetime.utcnow()
        snapshot = task.to_status_dict() if kind == "cv" else task.status_dict()
        if kind == "cv":
            record.department = getattr(task, "department", "") or record.department
            resume_data = getattr(task, "resume_data", None) or {}
            record.position = (
                getattr(task, "job_position", "")
                or resume_data.get("position", "")
                or record.position
            )
        # Task status metadata is enough for retrieval; do not duplicate candidate content.
        record.snapshot = json.dumps({k: v for k, v in snapshot.items()
                                      if k not in {"result", "content", "resume_data"}}, default=str)
        if task.status == "completed":
            paths = {"pptx": task.output_path} if kind == "cv" else {"docx": task.docx_path, "pdf": task.pdf_path}
            if kind == "cv" and task.output_path:
                paths["pdf"] = getattr(task, "pdf_path", None) or str(Path(task.output_path).with_suffix(".pdf"))
            destination = settings.output_path / "archive" / task.task_id
            destination.mkdir(parents=True, exist_ok=True)
            files = {}
            for extension, value in paths.items():
                source = Path(value) if value else None
                if source and source.is_file():
                    target = destination / (cv_download_filename(source.name) if kind == "cv" else source.name)
                    shutil.copy2(source, target)
                    files[extension] = str(target.resolve())
            record.files = json.dumps(files)
        owner_id = record.owner_id
        db.commit()
    if previous != task.status:
        audit(f"{kind}.task.{task.status}", 500 if task.status == "failed" else 200,
              task.task_id, {"id": owner_id})


def resource_data(item):
    files = json.loads(item.files)
    return {"id": item.id, "owner_id": item.owner_id, "kind": item.kind, "name": cv_download_filename(item.name) if item.kind == "legacy" else item.name,
            "department": item.department or "", "position": item.position or "",
            "status": item.status, "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "files": [{"format": ext, "name": cv_download_filename(Path(path).name), "available": Path(path).is_file()}
                      for ext, path in files.items()]}


def import_legacy_outputs():
    # In-memory jobs cannot resume across a process restart; never report them as still running.
    with SessionLocal() as db:
        db.query(Resource).filter(Resource.kind.in_(["cv", "jd"]), Resource.status.in_(["pending", "processing", "awaiting_input"])).update({Resource.status: "interrupted"})
        db.commit()
    root = settings.output_path.resolve()
    with SessionLocal() as db:
        registered_paths = {str(Path(value).resolve()) for row in db.query(Resource).filter(Resource.kind.in_(["cv", "jd"])).all()
                            for value in json.loads(row.files).values()}
        registered_names = {Path(path).name for path in registered_paths}
        for path in root.rglob("*"):
            if "archive" in path.relative_to(root).parts or not path.is_file() or path.suffix.lower() not in {".pptx", ".pdf", ".docx"}:
                continue
            if cv_download_filename(path.name) in {cv_download_filename(name) for name in registered_names} or not path.resolve().is_relative_to(root):
                continue
            rid = "legacy-" + hashlib.sha256(str(path.relative_to(root)).encode()).hexdigest()
            if not db.get(Resource, rid):
                db.add(Resource(id=rid, kind="legacy", name=path.name, status="completed",
                                files=json.dumps({path.suffix[1:]: str(path.resolve())})))
        db.commit()
