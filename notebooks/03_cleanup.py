# Databricks notebook source
# MAGIC %md
# MAGIC # Job Watch cleanup
# MAGIC Optional manual cleanup notebook. Run only when you decide to purge old/experimental rows.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview source/provider counts

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   provider,
# MAGIC   scrape_mode,
# MAGIC   source,
# MAGIC   COUNT(*) AS rows,
# MAGIC   MAX(last_seen_at) AS latest_seen_at
# MAGIC FROM job_watch.silver_seek_results
# MAGIC GROUP BY provider, scrape_mode, source
# MAGIC ORDER BY rows DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cleanup examples
# MAGIC Uncomment only what you want to remove.

# COMMAND ----------

# DBTITLE 1,manual cleanup examples
# Remove old Google/news experiments:
# spark.sql("DELETE FROM job_watch.silver_seek_results WHERE source LIKE 'google_%'")

# Refresh one direct provider/source after parser changes:
# spark.sql("DELETE FROM job_watch.silver_seek_results WHERE source = 'trademe'")

# Remove one provider completely:
# spark.sql("DELETE FROM job_watch.silver_seek_results WHERE provider = 'google'")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Rebuild gold after cleanup

# COMMAND ----------

MIN_RATE = 125

spark.sql(f"""
CREATE OR REPLACE TABLE job_watch.gold_seek_high_rate_roles AS
SELECT
  provider,
  scrape_mode,
  source,
  result_id,
  title,
  url,
  content,
  hourly_min,
  hourly_max,
  last_seen_at
FROM job_watch.silver_seek_results
WHERE hourly_max >= {MIN_RATE}
ORDER BY hourly_max DESC, last_seen_at DESC
""")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT *
# MAGIC FROM job_watch.gold_seek_high_rate_roles
# MAGIC ORDER BY hourly_max DESC, last_seen_at DESC;
