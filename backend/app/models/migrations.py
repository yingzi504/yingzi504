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

