"""Tiny Databricks SQL migration runner for job_watch Delta tables."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from .sql_assets import find_sql_dir, render_sql_asset

SCHEMA = "job_watch"
MIGRATIONS_TABLE = f"{SCHEMA}.schema_migrations"
DUPLICATE_COLUMN_MARKERS = (
    "already exists",
    "duplicate column",
    "field already exists",
    "column_already_exists",
)


def find_migrations_dir() -> Path:
    """Find sql/migrations from local runs or Databricks Repos/Workspace files."""
    migrations_dir = find_sql_dir() / "migrations"
    if migrations_dir.exists():
        return migrations_dir
    raise FileNotFoundError("Could not find sql/migrations directory")


def read_migration_files(migrations_dir: Path | None = None) -> list[Path]:
    directory = migrations_dir or find_migrations_dir()
    return sorted(path for path in directory.glob("*.sql") if path.is_file())


def split_sql_statements(sql_text: str) -> list[str]:
    """Split simple migration SQL files on semicolons, ignoring full-line comments."""
    lines = [line for line in sql_text.splitlines() if not line.strip().startswith("--")]
    return [statement.strip() for statement in "\n".join(lines).split(";") if statement.strip()]


def migration_id(path: Path) -> str:
    return path.name


def ensure_migrations_table(spark) -> None:
    values = {"schema": SCHEMA, "migrations_table": MIGRATIONS_TABLE}
    spark.sql(render_sql_asset("migration_control/create_schema.sql", values))
    spark.sql(render_sql_asset("migration_control/create_schema_migrations.sql", values))


def applied_migrations(spark) -> set[str]:
    ensure_migrations_table(spark)
    return {row["migration_id"] for row in spark.table(MIGRATIONS_TABLE).select("migration_id").collect()}


def _is_duplicate_column_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in DUPLICATE_COLUMN_MARKERS)


def record_migration(spark, migration_name: str) -> None:
    values = {
        "migrations_table": MIGRATIONS_TABLE,
        "migration_id": migration_name,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    spark.sql(render_sql_asset("migration_control/record_schema_migration.sql", values))


def run_migrations(spark, migrations_dir: Path | None = None) -> list[str]:
    """Apply pending .sql migrations and return the migration ids applied."""
    applied = applied_migrations(spark)
    newly_applied: list[str] = []

    for path in read_migration_files(migrations_dir):
        name = migration_id(path)
        if name in applied:
            continue

        statements = split_sql_statements(path.read_text(encoding="utf-8"))
        for statement in statements:
            try:
                spark.sql(statement)
            except Exception as exc:
                if re.match(r"(?is)^\s*alter\s+table\s+.+\s+add\s+columns?\b", statement) and _is_duplicate_column_error(exc):
                    continue
                raise

        record_migration(spark, name)
        newly_applied.append(name)

    return newly_applied
