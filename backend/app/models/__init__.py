# Database models
from app.models.database import Base, engine, SessionLocal, get_db
from app.models.task import ProcessingTask
from app.models.history import ProcessingHistory
from app.models.template import Template   # ← 步骤4.5
from app.models.jd import JD               # ← 步骤4.5

# 自动建表（幂等）
from app.models.access import User, LoginSession, AuditEvent, Resource

Base.metadata.create_all(bind=engine)

from app.models.migrations import ensure_runtime_columns

ensure_runtime_columns()
