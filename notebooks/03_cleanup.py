# Databricks notebook source
# MAGIC %md
# MAGIC # Job Watch cleanup
# MAGIC Wipes all Job Watch data while keeping the tables.

# COMMAND ----------

# DBTITLE 1,bootstrap job watch imports
# MAGIC %run ./_bootstrap

# COMMAND ----------

# DBTITLE 1,wipe data tables
truncated_tables = DB.truncate_data_tables(spark)

for table in DB.data_tables():
    if table in truncated_tables:
        print(f"Wiped {table}")
    else:
        print(f"Skipped missing table: {table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify

# COMMAND ----------

for table in DB.data_tables():
    if spark.catalog.tableExists(table):
        count = spark.table(table).count()
        print(f"{table}: {count} rows")
