# Databricks notebook source
# MAGIC %md
# MAGIC # Job Watch results
# MAGIC View high-rate Auckland software/development contract roles.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   title,
# MAGIC   hourly_min,
# MAGIC   hourly_max,
# MAGIC   url,
# MAGIC   content,
# MAGIC   last_seen_at
# MAGIC FROM job_watch.gold_seek_high_rate_roles
# MAGIC ORDER BY hourly_max DESC, last_seen_at DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   source,
# MAGIC   COUNT(*) AS total_rows,
# MAGIC   COUNT(hourly_max) AS rows_with_rate,
# MAGIC   MAX(hourly_max) AS max_rate,
# MAGIC   MAX(last_seen_at) AS latest_seen_at
# MAGIC FROM job_watch.silver_seek_results
# MAGIC GROUP BY source
# MAGIC ORDER BY total_rows DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   source,
# MAGIC   title,
# MAGIC   url,
# MAGIC   content,
# MAGIC   hourly_min,
# MAGIC   hourly_max,
# MAGIC   last_seen_at
# MAGIC FROM job_watch.silver_seek_results
# MAGIC ORDER BY last_seen_at DESC
# MAGIC LIMIT 100;
