"""Shared Databricks table names, schemas, and SQL operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .sql_assets import render_sql_asset
from .table_models import BRONZE_SEARCH_RUNS, GOLD_HIGH_RATE_ROLES, SILVER_RESULTS


@dataclass(frozen=True)
class JobWatchDatabase:
    """Central object for database structure used by notebooks and jobs."""

    schema: str = "job_watch"
    bronze_runs_name: str = "bronze_search_runs"
    silver_results_name: str = "silver_seek_results"
    gold_high_rate_roles_name: str = "gold_seek_high_rate_roles"
    new_results_view: str = "new_seek_results"

    @property
    def bronze_runs_table(self) -> str:
        return f"{self.schema}.{self.bronze_runs_name}"

    @property
    def silver_results_table(self) -> str:
        return f"{self.schema}.{self.silver_results_name}"

    @property
    def gold_high_rate_roles_table(self) -> str:
        return f"{self.schema}.{self.gold_high_rate_roles_name}"

    def sql_values(self, **extra: Any) -> dict[str, Any]:
        return {
            "bronze_runs_table": self.bronze_runs_table,
            "silver_results_table": self.silver_results_table,
            "gold_high_rate_roles_table": self.gold_high_rate_roles_table,
            "new_results_view": self.new_results_view,
            "silver_merge_update_assignments": SILVER_RESULTS.merge_update_assignments(
                exclude=("source", "result_id", "first_seen_at")
            ),
            "silver_insert_columns": SILVER_RESULTS.columns_csv(),
            "silver_insert_values": SILVER_RESULTS.aliased_columns_csv("source"),
            "gold_select_columns": GOLD_HIGH_RATE_ROLES.columns_csv(),
            "recent_silver_select_columns": SILVER_RESULTS.columns_csv(
                columns=(
                    "provider",
                    "scrape_mode",
                    "source",
                    "title",
                    "url",
                    "content",
                    "hourly_min",
                    "hourly_max",
                    "last_seen_at",
                )
            ),
            **extra,
        }

    def bronze_schema(self):
        return BRONZE_SEARCH_RUNS.spark_schema()

    def silver_schema(self):
        return SILVER_RESULTS.spark_schema()

    def append_bronze_rows(self, spark, rows: list[dict]) -> None:
        from pyspark.sql import functions as F

        df = spark.createDataFrame(rows, self.bronze_schema()).withColumn(
            "fetched_at", F.to_timestamp("fetched_at")
        )
        df.write.mode("append").saveAsTable(self.bronze_runs_table)

    def merge_silver_rows(self, spark, rows: list[dict]) -> None:
        from pyspark.sql import functions as F

        df = (
            spark.createDataFrame(rows, self.silver_schema())
            .dropDuplicates(["source", "result_id"])
            .withColumn("first_seen_at", F.to_timestamp("first_seen_at"))
            .withColumn("last_seen_at", F.to_timestamp("last_seen_at"))
        )
        df.createOrReplaceTempView(self.new_results_view)
        spark.sql(render_sql_asset("queries/merge_silver_results.sql", self.sql_values()))

    def rebuild_gold_high_rate_roles(self, spark, min_rate: float | int) -> None:
        spark.sql(
            render_sql_asset(
                "queries/rebuild_gold_high_rate_roles.sql",
                self.sql_values(min_rate=min_rate),
            )
        )

    def high_rate_roles_df(self, spark):
        return spark.sql(
            render_sql_asset("queries/select_gold_high_rate_roles.sql", self.sql_values())
        )

    def source_summary_df(self, spark):
        return spark.sql(render_sql_asset("queries/select_source_summary.sql", self.sql_values()))

    def recent_silver_results_df(self, spark, limit: int = 100):
        return spark.sql(
            render_sql_asset(
                "queries/select_recent_silver_results.sql",
                self.sql_values(limit=limit),
            )
        )

    def data_tables(self) -> list[str]:
        return [
            self.bronze_runs_table,
            self.silver_results_table,
            self.gold_high_rate_roles_table,
        ]

    def truncate_table(self, spark, table: str) -> None:
        spark.sql(render_sql_asset("queries/truncate_table.sql", {"table": table}))

    def truncate_data_tables(self, spark) -> list[str]:
        truncated = []
        for table in self.data_tables():
            if spark.catalog.tableExists(table):
                self.truncate_table(spark, table)
                truncated.append(table)
        return truncated
