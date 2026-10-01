"""Idempotent additive startup migrations (no Alembic in this project).

create_all never alters existing tables, so columns added after the first
deployment are brought in here. Runs AFTER create_all and BEFORE seeding.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from app.database import engine

# Dialect-specific DDL for the two new market_days columns.
_ADD_COLUMNS = {
    "rainy": {
        "postgresql": "ALTER TABLE market_days ADD COLUMN rainy BOOLEAN NOT NULL DEFAULT FALSE",
        "sqlite": "ALTER TABLE market_days ADD COLUMN rainy BOOLEAN NOT NULL DEFAULT 0",
    },
    "width_coefficient": {
        "postgresql": "ALTER TABLE market_days ADD COLUMN width_coefficient DOUBLE PRECISION NULL",
        "sqlite": "ALTER TABLE market_days ADD COLUMN width_coefficient FLOAT NULL",
    },
}


def run_startup_migrations() -> None:
    inspector = inspect(engine)
    if "market_days" not in inspector.get_table_names():
        return  # create_all will build the table with the new columns directly
    existing = {c["name"] for c in inspector.get_columns("market_days")}
    dialect = engine.dialect.name
    ddl_by_dialect = "postgresql" if dialect == "postgresql" else "sqlite"
    with engine.begin() as conn:
        for column, ddl_map in _ADD_COLUMNS.items():
            if column not in existing:
                conn.execute(text(ddl_map[ddl_by_dialect]))
