from sqlalchemy import inspect

from app.models.database import engine


JD_COLUMNS = {
    "department": "VARCHAR(200) DEFAULT ''",
    "tags_json": "TEXT DEFAULT '[]'",
    "structured_data": "TEXT DEFAULT ''",
    "active": "BOOLEAN DEFAULT 1",
    "source_task_id": "VARCHAR(36) DEFAULT ''",
}

ACCESS_RESOURCE_COLUMNS = {
    "department": "VARCHAR(50) NOT NULL DEFAULT ''",
    "position": "VARCHAR(200) NOT NULL DEFAULT ''",
}

ACCESS_AUDIT_COLUMNS = {
    "category": "VARCHAR(20) NOT NULL DEFAULT ''",
    "actor_role": "VARCHAR(20) NOT NULL DEFAULT ''",
    "account_type": "VARCHAR(50) NOT NULL DEFAULT ''",
    "resource_type": "VARCHAR(20) NOT NULL DEFAULT ''",
    "department": "VARCHAR(50) NOT NULL DEFAULT ''",
    "target_user_id": "INTEGER",
    "result": "VARCHAR(20) NOT NULL DEFAULT ''",
}

ACCESS_USER_COLUMNS = {
    "auth_version": "INTEGER NOT NULL DEFAULT 1",
}

ACCESS_SESSION_COLUMNS = {
    "auth_version": "INTEGER NOT NULL DEFAULT 1",
}


def ensure_runtime_columns() -> None:
    """Add forward-compatible SQLite columns without rebuilding user data."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    with engine.begin() as connection:
        if "jds" in tables:
            existing = {column["name"] for column in inspector.get_columns("jds")}
            for name, sql_type in JD_COLUMNS.items():
                if name not in existing:
                    connection.exec_driver_sql(f"ALTER TABLE jds ADD COLUMN {name} {sql_type}")
        if "access_resources" in tables:
            existing = {column["name"] for column in inspector.get_columns("access_resources")}
            for name, sql_type in ACCESS_RESOURCE_COLUMNS.items():
                if name not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE access_resources ADD COLUMN {name} {sql_type}"
                    )
        if "access_users" in tables:
            existing = {column["name"] for column in inspector.get_columns("access_users")}
            for name, sql_type in ACCESS_USER_COLUMNS.items():
                if name not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE access_users ADD COLUMN {name} {sql_type}"
                    )
        if "access_sessions" in tables:
            existing = {column["name"] for column in inspector.get_columns("access_sessions")}
            for name, sql_type in ACCESS_SESSION_COLUMNS.items():
                if name not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE access_sessions ADD COLUMN {name} {sql_type}"
                    )
        if "access_audit" in tables:
            existing = {column["name"] for column in inspector.get_columns("access_audit")}
            for name, sql_type in ACCESS_AUDIT_COLUMNS.items():
                if name not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE access_audit ADD COLUMN {name} {sql_type}"
                    )
            for name in ("category", "resource_type", "department", "result", "target_user_id"):
                connection.exec_driver_sql(
                    f"CREATE INDEX IF NOT EXISTS ix_access_audit_{name} ON access_audit ({name})"
                )

