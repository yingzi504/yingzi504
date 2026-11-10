"""Cookie sessions, API authorization and administrator reporting."""
import hashlib
import json
import math
import secrets
from datetime import datetime, timedelta, timezone
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
    FEATURES, ADMIN_ROLES, audit, create_user, current_actor, is_admin_role, is_superadmin,
    normalize_email, owned_resource,
    password_hash, password_matches, public_user, resource_data,
    AUDIT_CATEGORIES, masked_ip,
)

COOKIE = "resume_session"
router = APIRouter()
dummy_hash = password_hash(secrets.token_urlsafe(32))
RECRUITMENT_RULES = {"salaryMonths": 12, "bonusMonths": 2, "annualHours": 1880,
                     "overhead": 169200, "dailyHours": 8}
RECRUITMENT_CITIES = [
    {"id":"SH", "name":"上海", "row":3, "socialMin":7546, "socialMax":37731, "housingMin":2740, "housingMax":37731, "medicalBp":1050, "injuryBp":16, "housingBp":700, "supplementalBp":800, "seriousMedical":0},
    {"id":"BJ", "name":"北京", "row":4, "socialMin":7270, "socialMax":36348, "housingMin":2540, "housingMax":36348, "medicalBp":900, "injuryBp":20, "housingBp":1200, "supplementalBp":0, "seriousMedical":3},
    {"id":"HF", "name":"合肥", "row":5, "socialMin":4311, "socialMax":21556, "housingMin":3787, "housingMax":31564, "medicalBp":640, "injuryBp":20, "housingBp":1200, "supplementalBp":0, "seriousMedical":0},
    {"id":"SY", "name":"沈阳", "row":6, "socialMin":4533, "socialMax":22665, "housingMin":4533, "housingMax":30657, "medicalBp":860, "injuryBp":70, "housingBp":1200, "supplementalBp":0, "seriousMedical":0},
    {"id":"WH", "name":"芜湖", "row":7, "socialMin":4311, "socialMax":21556, "housingMin":2170, "housingMax":26991, "medicalBp":900, "injuryBp":20, "housingBp":1200, "supplementalBp":0, "seriousMedical":0},
]


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
    if not is_admin_role(user):
        raise HTTPException(403, "需要管理员权限")
    return user


def require_superadmin(request: Request):
    user = require_user(request)
    if user["must_change_password"]:
        raise HTTPException(403, "请先修改初始密码")
    if not is_superadmin(user):
        raise HTTPException(403, "需要超级管理员权限")
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
        if not is_admin_role(user) and not ({"cv", "jd"} & set(user["permissions"])):
            raise HTTPException(403, "此账号没有上传权限")
    elif path.startswith("/resume"):
        # Legacy diagnostic endpoints accept raw text/paths and are admin-only.
        if not is_admin_role(user):
            raise HTTPException(403, "此接口仅供管理员使用")
    if feature and not is_admin_role(user) and feature not in user["permissions"]:
        raise HTTPException(403, "此账号未开通该功能")
    if path.startswith("/jd-conversion/") and path.endswith("/save") and not is_admin_role(user) and "library" not in user["permissions"]:
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
                if user and user.active and session.auth_version == user.auth_version:
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
                  request.client.host if request.client else None,
                  target_user_id=params.get("user_id"))
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
                            auth_version=user.auth_version,
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
        row.auth_version += 1
        # Keep only the current session; revoke other devices.
        current_hash = token_digest(request.cookies.get(COOKIE, ""))
        db.query(LoginSession).filter(LoginSession.user_id == row.id,
            LoginSession.token_hash != current_hash).delete()
        current_session = db.get(LoginSession, current_hash)
        if current_session:
            current_session.auth_version = row.auth_version
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
    if body.role == "admin" and not is_superadmin(admin):
        raise HTTPException(403, "只有超级管理员可以授权管理员角色")
    with SessionLocal() as db:
        try:
            user = create_user(db, body.email, body.role, body.account_type, body.permissions)
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "此邮箱已存在")
        audit("admin.user.created", resource_id=str(user.id), actor=admin)
        return {"success": True, "data": public_user(user)}


@router.post("/superadmin/users/{user_id}/grant-admin")
def grant_admin(user_id: int, superadmin=Depends(require_superadmin)):
    with SessionLocal() as db:
        row = db.get(User, user_id)
        if not row:
            raise HTTPException(404, "账号不存在")
        if row.role == "superadmin":
            raise HTTPException(400, "该账号已经是超级管理员")
        if row.role == "admin":
            return {"success": True, "data": public_user(row)}
        row.role = "admin"
        row.active = True
        row.must_change_password = True
        row.auth_version += 1
        db.query(LoginSession).filter_by(user_id=row.id).delete()
        db.commit()
        db.refresh(row)
        audit("admin.user.role_granted", resource_id=str(row.id), actor=superadmin, target_user_id=row.id)
        return {"success": True, "data": public_user(row)}


@router.post("/superadmin/users/{user_id}/revoke-admin")
def revoke_admin(user_id: int, superadmin=Depends(require_superadmin)):
    """Downgrade an administrator to a member and revoke active sessions."""
    with SessionLocal() as db:
        row = db.get(User, user_id)
        if not row:
            raise HTTPException(404, "账号不存在")
        if row.role == "superadmin":
            raise HTTPException(400, "不能收回超级管理员权限")
        if row.role != "admin":
            return {"success": True, "data": public_user(row)}
        row.role = "member"
        row.auth_version += 1
        db.query(LoginSession).filter_by(user_id=row.id).delete()
        db.commit()
        db.refresh(row)
        audit("admin.user.role_revoked", resource_id=str(row.id), actor=superadmin, target_user_id=row.id)
        return {"success": True, "data": public_user(row)}


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
        if row.role in ADMIN_ROLES and not is_superadmin(admin):
            raise HTTPException(403, "只有超级管理员可以修改管理员账号")
        if is_superadmin(row) and (not body.active or not is_superadmin(admin)):
            raise HTTPException(400, "不可停用或降级超级管理员账号")
        if is_superadmin(row) and db.query(User).filter_by(role="superadmin", active=True).count() <= 1 and not body.active:
            raise HTTPException(400, "系统必须保留至少一个启用的超级管理员")
        permissions = json.dumps(body.permissions)
        security_changed = row.active != body.active or row.permissions != permissions
        row.active, row.account_type = body.active, body.account_type
        row.permissions = permissions
        if security_changed:
            row.auth_version += 1
            db.query(LoginSession).filter_by(user_id=row.id).delete()
        db.commit()
        audit("admin.user.updated", resource_id=str(row.id), actor=admin, target_user_id=row.id)
        return {"success": True, "data": public_user(row)}


@router.post("/admin/users/{user_id}/reset-password")
def reset_password(user_id: int, admin=Depends(require_admin)):
    with SessionLocal() as db:
        row = db.get(User, user_id)
        if not row:
            raise HTTPException(404, "账号不存在")
        if is_superadmin(row):
            raise HTTPException(403, "超级管理员密码只能由本人修改")
        if is_admin_role(row) and not is_superadmin(admin):
            raise HTTPException(403, "只有超级管理员可以重置管理员密码")
        row.password_hash, row.must_change_password = password_hash("123456"), True
        row.auth_version += 1
        db.query(LoginSession).filter_by(user_id=row.id).delete()
        db.commit()
    audit("admin.user.password_reset", resource_id=str(user_id), actor=admin, target_user_id=user_id)
    return {"success": True}


@router.get("/admin/statistics")
def statistics(admin=Depends(require_admin)):
    with SessionLocal() as db:
        now = datetime.utcnow()
        online_users = db.query(func.count(func.distinct(LoginSession.user_id))).filter(
            LoginSession.expires_at > now
        ).scalar() or 0
        return {"success": True, "data": {
            "users": db.query(User).count(), "active_users": db.query(User).filter_by(active=True).count(),
            "logged_in_users": online_users,
            "users_ever_logged_in": db.query(User).filter(User.last_login_at.isnot(None)).count(),
            "tasks": db.query(Resource).filter(Resource.kind.in_(["cv", "jd"])).count(),
            "completed": db.query(Resource).filter(Resource.kind.in_(["cv", "jd"]), Resource.status == "completed").count(),
            "operations": db.query(AuditEvent).count()}}


@router.get("/superadmin/statistics")
def superadmin_statistics(superadmin=Depends(require_superadmin)):
    return statistics(superadmin)


@router.get("/admin/tools/recruitment-config")
def recruitment_tool_config(admin=Depends(require_admin)):
    """Return confidential recruitment calculation policy only to administrators."""
    return {"success": True, "data": {
        "rules": RECRUITMENT_RULES,
        "cities": RECRUITMENT_CITIES,
    }}


class RecruitmentPlanInput(BaseModel):
    id: int
    isCurrent: bool = False
    city: Literal["SH", "BJ", "HF", "SY", "WH"] = "SH"
    basePay: float | None = Field(None, ge=0, le=100_000_000)
    onsite: float | None = Field(None, ge=0, le=100_000_000)
    annualBonus: float | None = Field(None, ge=0, le=100_000_000)
    projectBonus: float | None = Field(None, ge=0, le=100_000_000)
    benefits: float | None = Field(None, ge=0, le=100_000_000)
    supplementary: float | None = Field(None, ge=0, le=100_000_000)
    contributionMode: Literal["salary", "priorYear"] = "salary"
    priorYearPay: float | None = Field(None, ge=0, le=100_000_000)


class RecruitmentCalculationRequest(BaseModel):
    plans: list[RecruitmentPlanInput] = Field(min_length=1, max_length=20)


def _recruitment_calculation(plans: list[RecruitmentPlanInput]):
    cities = {city["id"]: city for city in RECRUITMENT_CITIES}

    def cents(value):
        return math.floor(value * 100 + 0.5)

    def money_sum(values):
        return sum(cents(value) for value in values) / 100

    def bonus(plan):
        if plan.isCurrent:
            return plan.annualBonus
        return cents(plan.basePay) * RECRUITMENT_RULES["bonusMonths"] / 100 if plan.basePay is not None else None

    def total(plan):
        values = [plan.basePay, plan.onsite, bonus(plan), plan.projectBonus, plan.benefits, plan.supplementary]
        if any(value is None for value in values):
            return None
        return money_sum([values[0] * RECRUITMENT_RULES["salaryMonths"], *values[1:]])

    def contributions(city_id, salary):
        if salary is None:
            return None
        policy = cities[city_id]
        clamp = lambda low, high: max(low, min(high, cents(salary) / 100))
        social = round(clamp(policy["socialMin"], policy["socialMax"])) if city_id == "SH" else clamp(policy["socialMin"], policy["socialMax"])
        housing = round(clamp(policy["housingMin"], policy["housingMax"])) if city_id == "SH" else clamp(policy["housingMin"], policy["housingMax"])

        def fee(base, bp, mode):
            product = cents(base) * bp
            if mode == "up1":
                return math.ceil(product / 100000) / 10
            if mode == "round0":
                return math.floor(product / 1000000 + 0.5)
            return math.floor(product / 10000 + 0.5) / 100

        pct = lambda bp: f"{bp / 100:g}%"
        lines = [
            {"key":"pension","name":"养老保险","base":social,"employeeRate":"8%","employerRate":"16%","employee":fee(social,800,"up1"),"employer":fee(social,1600,"round2")},
            {"key":"medical","name":"医疗保险","base":social,"employeeRate":"2%","employerRate":pct(policy["medicalBp"]),"employee":fee(social,200,"up1"),"employer":fee(social,policy["medicalBp"],"round2")},
            {"key":"serious","name":"大病医疗","base":None,"employeeRate":"固定 3 元" if policy["seriousMedical"] else "未设置","employerRate":"未设置","employee":policy["seriousMedical"],"employer":0},
            {"key":"unemployment","name":"失业保险","base":social,"employeeRate":"0.5%","employerRate":"0.5%","employee":fee(social,50,"up1"),"employer":fee(social,50,"round2")},
            {"key":"maternity","name":"生育保险","base":social,"employeeRate":"未设置","employerRate":"0.8%","employee":0,"employer":fee(social,80,"round2")},
            {"key":"injury","name":"工伤保险","base":social,"employeeRate":"未设置","employerRate":pct(policy["injuryBp"]),"employee":0,"employer":fee(social,policy["injuryBp"],"round2")},
            {"key":"housing","name":"住房公积金","base":housing,"employeeRate":pct(policy["housingBp"]),"employerRate":pct(policy["housingBp"]),"employee":fee(housing,policy["housingBp"],"round0"),"employer":fee(housing,policy["housingBp"],"round0")},
            {"key":"supplemental","name":"补充公积金","base":housing,"employeeRate":"未设置","employerRate":"8% · 取整" if policy["supplementalBp"] else "未设置","employee":0,"employer":fee(housing,policy["supplementalBp"],"round0")},
        ]
        employee, employer = money_sum([line["employee"] for line in lines]), money_sum([line["employer"] for line in lines])
        return {"socialBase":social,"housingBase":housing,"lines":lines,"employee":employee,"employer":employer,"total":money_sum([employee, employer])}

    totals = {plan.id: total(plan) for plan in plans}
    baseline = next((totals[plan.id] for plan in plans if plan.isCurrent), None)
    output = {}
    labels = (("税前月薪", "basePay"), ("驻场津贴", "onsite"), ("年终奖", "annualBonus"),
              ("项目奖金", "projectBonus"), ("年度福利", "benefits"), ("年包补充公积金", "supplementary"))
    for plan in plans:
        annual_bonus = bonus(plan)
        missing = [label for label, field in labels if (annual_bonus if field == "annualBonus" else getattr(plan, field)) is None]
        salary = plan.priorYearPay if plan.contributionMode == "priorYear" else plan.basePay
        city_results = {}
        for city_id in cities:
            contribution = contributions(city_id, salary)
            rate = None
            package = totals[plan.id]
            if package is not None and plan.supplementary is not None and contribution:
                deduction = plan.supplementary if city_id == "SH" else 0
                cost_package = money_sum([package, -deduction])
                annual_cost = money_sum([cost_package, contribution["employer"] * 12])
                with_overhead = money_sum([annual_cost, RECRUITMENT_RULES["overhead"]])
                hours, daily_hours = RECRUITMENT_RULES["annualHours"], RECRUITMENT_RULES["dailyHours"]
                rate = {"annualCost":annual_cost,"withOverhead":with_overhead,
                        "hourly":annual_cost/hours,"hourlyWithOverhead":with_overhead/hours,
                        "daily":annual_cost/hours*daily_hours,"dailyWithOverhead":with_overhead/hours*daily_hours,
                        "packageSupplementDeduction":deduction,"costPackage":cost_package}
            city_results[city_id] = {"contributions": contribution, "rates": rate}
        increase = None
        if totals[plan.id] is not None and baseline not in (None, 0):
            delta = cents(totals[plan.id]) - cents(baseline)
            increase = (1 if delta >= 0 else -1) * math.floor(abs(delta) * 100 / cents(baseline) + 0.5) / 100
        output[str(plan.id)] = {"annualBonus":annual_bonus,"totalPackage":totals[plan.id],
                                "missingFields":missing,"increaseRate":increase,"cities":city_results}
    return output


@router.post("/admin/tools/recruitment-calculate")
def recruitment_tool_calculate(body: RecruitmentCalculationRequest, admin=Depends(require_admin)):
    return {"success": True, "data": _recruitment_calculation(body.plans)}


def audit_filters(
    user_id: int | None = Query(None, ge=1),
    action: str = Query("", max_length=120),
    category: str = Query("", max_length=20),
    resource_type: str = Query("", max_length=20),
    result: Literal["", "success", "failed"] = "",
    account_type: str = Query("", max_length=50),
    department: str = Query("", max_length=50),
    resource_id: str = Query("", max_length=120),
    start: datetime | None = None,
    end: datetime | None = None,
):
    if category and category not in AUDIT_CATEGORIES:
        raise HTTPException(422, "操作分类无效")
    # API timestamps use ISO 8601; normalize offsets before comparing SQLite UTC.
    def utc(value):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value
    start, end = utc(start), utc(end)
    if start and end and start > end:
        raise HTTPException(422, "开始时间不能晚于结束时间")
    return dict(user_id=user_id, action=action, category=category, resource_type=resource_type,
                result=result, account_type=account_type, department=department,
                resource_id=resource_id, start=start, end=end)


def audit_listing(page, filters, user, personal=False):
    with SessionLocal() as db:
        q = db.query(AuditEvent).outerjoin(User, User.id == AuditEvent.user_id)
        owner = user["id"] if personal else filters["user_id"]
        if owner is not None:
            q = q.filter(AuditEvent.user_id == owner)
        for key in ("category", "resource_type", "result", "account_type", "department", "resource_id"):
            if filters[key]:
                q = q.filter(getattr(AuditEvent, key) == filters[key])
        if filters["action"]:
            q = q.filter(AuditEvent.action.contains(filters["action"], autoescape=True))
        if filters["start"]:
            q = q.filter(AuditEvent.created_at >= filters["start"])
        if filters["end"]:
            q = q.filter(AuditEvent.created_at <= filters["end"])
        total = q.count()
        counts = dict(q.with_entities(AuditEvent.category, func.count(AuditEvent.id)).group_by(AuditEvent.category).all())
        failed = q.filter(AuditEvent.status_code >= 400).count()
        rows = q.add_columns(User.email).order_by(AuditEvent.id.desc()).offset((page-1)*30).limit(30).all()
        data = []
        for event, email in rows:
            item = {"id": event.id, "email": email, "user_id": event.user_id,
                    "action": event.action, "category": event.category,
                    "category_label": AUDIT_CATEGORIES.get(event.category, "未分类"),
                    "actor_role": event.actor_role, "account_type": event.account_type,
                    "resource_type": event.resource_type, "department": event.department,
                    "target_user_id": event.target_user_id, "resource_id": event.resource_id,
                    "status_code": event.status_code, "result": event.result,
                    "created_at": event.created_at.isoformat() + "Z"}
            if not personal:
                item["ip_address"] = masked_ip(event.ip_address)
            data.append(item)
        return {"success": True, "total": total, "data": data,
                "categories": [{"value": key, "label": label} for key, label in AUDIT_CATEGORIES.items()],
                "summary": {"success": total-failed, "failed": failed, "by_category": counts}}


@router.get("/admin/audit")
def events(page: int = Query(1, ge=1), filters=Depends(audit_filters), admin=Depends(require_admin)):
    return audit_listing(page, filters, admin)


def ready_user(request: Request):
    user = require_user(request)
    if user["must_change_password"]:
        raise HTTPException(403, "请先修改初始密码")
    return user


@router.get("/audit")
def my_events(page: int = Query(1, ge=1), filters=Depends(audit_filters), user=Depends(ready_user)):
    # user_id supplied by a client can never widen the personal scope.
    return audit_listing(page, filters, user, personal=True)


@router.get("/records")
def records(page: int = Query(1, ge=1), user_id: int | None = None,
            status: str = Query("", max_length=30), kind: str = Query("", max_length=20),
            department: str = Query("", max_length=50), user=Depends(ready_user)):
    with SessionLocal() as db:
        q = db.query(Resource, User.email).outerjoin(User, User.id == Resource.owner_id).filter(Resource.kind != "upload")
        if not is_admin_role(user):
            q = q.filter(Resource.owner_id == user["id"])
        elif user_id is not None:
            q = q.filter(Resource.owner_id == user_id)
        if status:
            q = q.filter(Resource.status == status)
        if kind:
            q = q.filter(Resource.kind == kind)
        if department:
            q = q.filter(Resource.department == department)
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
    if not is_admin_role(user) and "cv" not in user["permissions"]:
        raise HTTPException(403, "此账号未开通 CV 功能")
    with SessionLocal() as db:
        base = db.query(Resource).filter(
            Resource.kind == "cv", Resource.status == "completed"
        )
        if not is_admin_role(user):
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
