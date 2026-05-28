"""First-class table/row models used to generate schemas and SQL fragments."""

from __future__ import annotations

from dataclasses import astuple, dataclass, fields
from typing import ClassVar


@dataclass(frozen=True)
class Column:
    name: str
    databricks_type: str


@dataclass(frozen=True)
class TableDefinition:
    name: str
    columns: tuple[Column, ...]

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    def spark_schema(self):
        from pyspark.sql.types import DoubleType, StringType, StructField, StructType

        spark_types = {
            "STRING": StringType(),
            "TIMESTAMP": StringType(),
            "DOUBLE": DoubleType(),
        }
        return StructType([
            StructField(column.name, spark_types[column.databricks_type])
            for column in self.columns
        ])

    def columns_csv(self, columns: tuple[str, ...] | None = None, indent: str = "  ") -> str:
        names = columns or self.column_names
        return ",\n".join(f"{indent}{name}" for name in names)

    def aliased_columns_csv(
        self,
        alias: str,
        columns: tuple[str, ...] | None = None,
        indent: str = "  ",
    ) -> str:
        names = columns or self.column_names
        return ",\n".join(f"{indent}{alias}.{name}" for name in names)

    def merge_update_assignments(
        self,
        source_alias: str = "source",
        target_alias: str = "target",
        exclude: tuple[str, ...] = (),
    ) -> str:
        excluded = set(exclude)
        return ",\n".join(
            f"  {target_alias}.{name} = {source_alias}.{name}"
            for name in self.column_names
            if name not in excluded
        )

    def sqlite_insert_sql(self, table_name: str) -> str:
        placeholders = ", ".join("?" for _ in self.column_names)
        return f"INSERT INTO {table_name} ({', '.join(self.column_names)}) VALUES ({placeholders})"


BRONZE_SEARCH_RUNS = TableDefinition(
    name="bronze_search_runs",
    columns=(
        Column("run_id", "STRING"),
        Column("source", "STRING"),
        Column("fetched_at", "TIMESTAMP"),
        Column("query", "STRING"),
        Column("response_json", "STRING"),
    ),
)

SILVER_RESULTS = TableDefinition(
    name="silver_seek_results",
    columns=(
        Column("provider", "STRING"),
        Column("scrape_mode", "STRING"),
        Column("source", "STRING"),
        Column("result_id", "STRING"),
        Column("title", "STRING"),
        Column("url", "STRING"),
        Column("content", "STRING"),
        Column("published", "STRING"),
        Column("raw_json", "STRING"),
        Column("hourly_min", "DOUBLE"),
        Column("hourly_max", "DOUBLE"),
        Column("first_seen_at", "TIMESTAMP"),
        Column("last_seen_at", "TIMESTAMP"),
    ),
)

GOLD_HIGH_RATE_ROLES = TableDefinition(
    name="gold_seek_high_rate_roles",
    columns=(
        Column("provider", "STRING"),
        Column("scrape_mode", "STRING"),
        Column("source", "STRING"),
        Column("result_id", "STRING"),
        Column("title", "STRING"),
        Column("url", "STRING"),
        Column("content", "STRING"),
        Column("hourly_min", "DOUBLE"),
        Column("hourly_max", "DOUBLE"),
        Column("last_seen_at", "TIMESTAMP"),
    ),
)


@dataclass(frozen=True)
class SilverResultRow:
    provider: str
    scrape_mode: str
    source: str
    result_id: str
    title: str
    url: str
    content: str
    published: str = ""
    raw_json: str = "{}"
    hourly_min: float | None = None
    hourly_max: float | None = None
    first_seen_at: str = "2026-01-01 00:00:00"
    last_seen_at: str = "2026-01-01 00:00:00"

    table: ClassVar[TableDefinition] = SILVER_RESULTS

    def as_dict(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    def values(self) -> tuple[object, ...]:
        return astuple(self)
