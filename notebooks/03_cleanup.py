# Databricks notebook source
# MAGIC %md
# MAGIC # Job Watch cleanup
# MAGIC Wipes all Job Watch data while keeping the tables.

# COMMAND ----------

TABLES = [
    "job_watch.bronze_search_runs",
    "job_watch.silver_seek_results",
    "job_watch.gold_seek_high_rate_roles",
]

for table in TABLES:
    if spark.catalog.tableExists(table):
        spark.sql(f"TRUNCATE TABLE {table}")
        print(f"Wiped {table}")
    else:
        print(f"Skipped missing table: {table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify

# COMMAND ----------

for table in TABLES:
    if spark.catalog.tableExists(table):
        count = spark.table(table).count()
        print(f"{table}: {count} rows")
