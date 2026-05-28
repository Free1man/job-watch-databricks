# Databricks notebook source
# MAGIC %md
# MAGIC # Job Watch results
# MAGIC View normalized job results by provider/source.

# COMMAND ----------

# DBTITLE 1,bootstrap job watch imports
# MAGIC %run ./_bootstrap

# COMMAND ----------

# DBTITLE 1,display high-rate roles
display(DB.high_rate_roles_df(spark))

# COMMAND ----------

# DBTITLE 1,display source summary
display(DB.source_summary_df(spark))

# COMMAND ----------

# DBTITLE 1,display recent silver results
display(DB.recent_silver_results_df(spark, limit=100))
