"""Helpers for loading SQL assets from the project sql/ directory."""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any


def find_sql_dir() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for start in candidates:
        for parent in (start, *start.parents):
            sql_dir = parent / "sql"
            if sql_dir.exists():
                return sql_dir
    raise FileNotFoundError("Could not find sql directory")


def read_sql_asset(relative_path: str, sql_dir: Path | None = None) -> str:
    base = sql_dir or find_sql_dir()
    return (base / relative_path).read_text(encoding="utf-8")


def render_sql_asset(relative_path: str, values: dict[str, Any], sql_dir: Path | None = None) -> str:
    template = Template(read_sql_asset(relative_path, sql_dir))
    return template.substitute({key: str(value) for key, value in values.items()})
