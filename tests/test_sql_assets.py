from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from job_watch.database import JobWatchDatabase
from job_watch.databricks_migrations import read_migration_files, split_sql_statements
from job_watch.sql_assets import render_sql_asset
from job_watch.table_models import SILVER_RESULTS, SilverResultRow


ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"


SILVER_FIXTURES = [
    SilverResultRow(
        provider="seek",
        scrape_mode="rss",
        source="seek",
        result_id="1",
        title="Senior .NET Contractor",
        url="https://www.seek.co.nz/job/1",
        content="$130/hour Auckland contract",
        hourly_min=120.0,
        hourly_max=130.0,
        last_seen_at="2026-01-02 00:00:00",
    ),
    SilverResultRow(
        provider="trademe",
        scrape_mode="html",
        source="trademe",
        result_id="2",
        title="Intermediate Developer",
        url="https://www.trademe.co.nz/a/jobs/listing/2",
        content="$90/hour Auckland contract",
        hourly_min=80.0,
        hourly_max=90.0,
        last_seen_at="2026-01-03 00:00:00",
    ),
]


def _sqlite_name(sql: str) -> str:
    return sql.replace("job_watch.", "job_watch_")


def _sqlite_types(sql: str) -> str:
    return (
        sql.replace("STRING", "TEXT")
        .replace("TIMESTAMP", "TEXT")
        .replace("DOUBLE", "REAL")
    )


def _sqlite_migration_statement(statement: str) -> str | None:
    if statement.upper().startswith("CREATE SCHEMA"):
        return None

    sql = _sqlite_types(_sqlite_name(statement))
    sql = re.sub(r"\s+USING\s+DELTA\s*$", "", sql, flags=re.IGNORECASE)

    alter_match = re.match(
        r"(?is)^ALTER\s+TABLE\s+(\S+)\s+ADD\s+COLUMNS\s*\((.+)\)$",
        sql.strip(),
    )
    if alter_match:
        return f"ALTER TABLE {alter_match.group(1)} ADD COLUMN {alter_match.group(2)}"

    return sql


def _execute_migrations_on_sqlite(conn: sqlite3.Connection) -> None:
    for path in read_migration_files(SQL_DIR / "migrations"):
        for statement in split_sql_statements(path.read_text(encoding="utf-8")):
            sqlite_statement = _sqlite_migration_statement(statement)
            if not sqlite_statement:
                continue
            try:
                conn.execute(sqlite_statement)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise


def _render_query_for_sqlite(asset: str, **extra: object) -> str:
    db = JobWatchDatabase()
    sql = render_sql_asset(asset, db.sql_values(**extra), SQL_DIR)
    return _sqlite_name(sql).strip().rstrip(";")


def _insert_silver_rows(conn: sqlite3.Connection, table: str, rows: list[SilverResultRow]) -> None:
    conn.executemany(SILVER_RESULTS.sqlite_insert_sql(table), [row.values() for row in rows])


def _seed_silver_results(conn: sqlite3.Connection) -> None:
    db = JobWatchDatabase()
    table = _sqlite_name(db.silver_results_table)
    _insert_silver_rows(conn, table, SILVER_FIXTURES)


def test_migrations_create_expected_tables_from_existing_scripts():
    conn = sqlite3.connect(":memory:")

    _execute_migrations_on_sqlite(conn)

    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert {
        "job_watch_bronze_search_runs",
        "job_watch_silver_seek_results",
        "job_watch_gold_seek_high_rate_roles",
    }.issubset(tables)

    silver_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(job_watch_silver_seek_results)").fetchall()
    }
    assert set(SILVER_RESULTS.column_names).issubset(silver_columns)


def test_extracted_gold_and_summary_sql_return_meaningful_data():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _execute_migrations_on_sqlite(conn)
    _seed_silver_results(conn)

    rebuild_sql = _render_query_for_sqlite("queries/rebuild_gold_high_rate_roles.sql", min_rate=125)
    rebuild_sql = re.sub(
        r"(?is)^CREATE\s+OR\s+REPLACE\s+TABLE\s+(\S+)\s+AS",
        r"DROP TABLE IF EXISTS \1; CREATE TABLE \1 AS",
        rebuild_sql,
    )
    conn.executescript(rebuild_sql)

    high_rate_sql = _render_query_for_sqlite("queries/select_gold_high_rate_roles.sql")
    high_rate_rows = conn.execute(high_rate_sql).fetchall()
    assert len(high_rate_rows) == 1
    assert high_rate_rows[0]["title"] == "Senior .NET Contractor"
    assert high_rate_rows[0]["hourly_max"] == 130.0

    summary_sql = _render_query_for_sqlite("queries/select_source_summary.sql")
    summary_rows = conn.execute(summary_sql).fetchall()
    assert {row["source"] for row in summary_rows} == {"seek", "trademe"}
    assert {row["rows_with_rate"] for row in summary_rows} == {1}

    recent_sql = _render_query_for_sqlite("queries/select_recent_silver_results.sql", limit=1)
    recent_rows = conn.execute(recent_sql).fetchall()
    assert len(recent_rows) == 1
    assert recent_rows[0]["source"] == "trademe"


def test_all_extracted_sql_assets_render_with_shared_database_object():
    db = JobWatchDatabase()
    assets = [
        "queries/merge_silver_results.sql",
        "queries/rebuild_gold_high_rate_roles.sql",
        "queries/select_gold_high_rate_roles.sql",
        "queries/select_source_summary.sql",
        "queries/select_recent_silver_results.sql",
        "queries/truncate_table.sql",
        "migration_control/create_schema.sql",
        "migration_control/create_schema_migrations.sql",
        "migration_control/record_schema_migration.sql",
    ]

    values = db.sql_values(
        min_rate=125,
        limit=100,
        table=db.bronze_runs_table,
        schema=db.schema,
        migrations_table=f"{db.schema}.schema_migrations",
        migration_id="001_initial_job_watch_tables.sql",
        applied_at="2026-01-01T00:00:00+00:00",
    )
    for asset in assets:
        sql = render_sql_asset(asset, values, SQL_DIR)
        assert "${" not in sql
        assert "job_watch" in sql
