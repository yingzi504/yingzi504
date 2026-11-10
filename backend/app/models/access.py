"""Persistent accounts, sessions, audit events and owned conversion resources."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from app.models.database import Base


class User(Base):
    __tablename__ = "access_users"
    id = Column(Integer, primary_key=True)
    email = Column(String(254), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False, default="member")
    account_type = Column(String(50), nullable=False, default="standard")
    permissions = Column(Text, nullable=False, default='["cv", "jd", "library", "templates", "terminology"]')
    active = Column(Boolean, nullable=False, default=True)
    must_change_password = Column(Boolean, nullable=False, default=True)
    auth_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)


class LoginSession(Base):
    __tablename__ = "access_sessions"
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("access_users.id"), index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    auth_version = Column(Integer, nullable=False, default=1)


class AuditEvent(Base):
    __tablename__ = "access_audit"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    action = Column(String(120), nullable=False)
    category = Column(String(20), nullable=False, default="", index=True)
    actor_role = Column(String(20), nullable=False, default="")
    account_type = Column(String(50), nullable=False, default="")
    resource_type = Column(String(20), nullable=False, default="", index=True)
    department = Column(String(50), nullable=False, default="", index=True)
    target_user_id = Column(Integer, index=True)
    result = Column(String(20), nullable=False, default="", index=True)
    resource_id = Column(String(120), index=True)
    status_code = Column(Integer, nullable=False)
    ip_address = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class Resource(Base):
    __tablename__ = "access_resources"
    id = Column(String(120), primary_key=True)
    owner_id = Column(Integer, ForeignKey("access_users.id"), index=True)
    kind = Column(String(20), nullable=False)
    name = Column(Text, nullable=False, default="")
    department = Column(String(50), nullable=False, default="", index=True)
    position = Column(String(200), nullable=False, default="", index=True)
    status = Column(String(30), nullable=False, default="pending")
    files = Column(Text, nullable=False, default="{}")
    snapshot = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
