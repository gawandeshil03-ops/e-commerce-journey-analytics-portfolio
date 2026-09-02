from __future__ import annotations

from pathlib import Path

import duckdb

from .config import (
    DATABASE_PATH,
    RAW_EVENTS_PATH,
    SESSION_GAP_MINUTES,
    SQL_DIR,
    ensure_directories,
)
from .data import validate_events_file


SQL_FILES = (
    "00_build_model.sql",
    "01_data_quality.sql",
    "02_product_metrics.sql",
    "03_retention.sql",
    "04_cart_recovery.sql",
)


def connect(database_path: Path = DATABASE_PATH, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(str(database_path), read_only=read_only)
    connection.execute("SET TimeZone = 'UTC'")
    return connection


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def render_sql(sql: str, replacements: dict[str, object]) -> str:
    rendered = sql
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("Unresolved SQL template placeholder.")
    return rendered


def build_database(
    events_path: Path = RAW_EVENTS_PATH,
    database_path: Path = DATABASE_PATH,
) -> duckdb.DuckDBPyConnection:
    ensure_directories()
    validate_events_file(events_path)

    connection = connect(database_path)
    replacements = {
        "EVENTS_CSV": _sql_literal(events_path.resolve().as_posix()),
        "SESSION_GAP_MS": SESSION_GAP_MINUTES * 60 * 1000,
    }

    for filename in SQL_FILES:
        sql = (SQL_DIR / filename).read_text(encoding="utf-8")
        connection.execute(render_sql(sql, replacements))

    return connection
