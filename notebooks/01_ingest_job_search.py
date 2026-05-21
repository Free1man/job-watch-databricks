# Databricks notebook source
# MAGIC %md
# MAGIC # Job Watch ingest
# MAGIC Public Bing RSS/search ingestion for Auckland software/development contract roles.
# MAGIC
# MAGIC RSS is still primary. Authorized direct scraping is enabled by config. No API keys.

# COMMAND ----------

# DBTITLE 1,install requests package
# MAGIC %pip install requests

# COMMAND ----------

# MAGIC %md
# MAGIC ## Imports and repo path setup

# COMMAND ----------

# DBTITLE 1,import libraries and configure job watch environment
import json
import os
import sys
import uuid
from datetime import datetime, timezone

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

# Make `src/job_watch` importable both in Databricks Repos and local runs.
for candidate in [
    os.path.abspath("../src"),
    os.path.abspath("./src"),
    "/Workspace/Repos/seek-job-watch/src",
]:
    if candidate not in sys.path and os.path.exists(candidate):
        sys.path.append(candidate)

from job_watch.config import (
    CUSTOM_RSS_FEEDS,
    DIRECT_SCRAPE_ENABLED,
    DIRECT_SOURCES,
    MIN_RATE,
    SEARCH_SOURCES,
)
from job_watch.direct_sources import direct_html_search
from job_watch.filters import is_probably_job_result, url_allowed
from job_watch.parsing import make_result_id, parse_hourly_rate
from job_watch.rss_sources import canonicalize_url, fetch_rss_url, source_search

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run config

# COMMAND ----------

# DBTITLE 1,generate run ID and fetch data retrieval details
RUN_ID = str(uuid.uuid4())
FETCHED_AT = datetime.now(timezone.utc)

print("RUN_ID:", RUN_ID)
print("FETCHED_AT:", FETCHED_AT.isoformat())
print("MIN_RATE:", MIN_RATE)
print("Search sources:", [s["source"] for s in SEARCH_SOURCES])
print("Direct scraping enabled:", DIRECT_SCRAPE_ENABLED)
print("Direct sources:", [s["source"] for s in DIRECT_SOURCES])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Delta schema/tables
# MAGIC
# MAGIC Table names still use the old `seek` names for compatibility.

# COMMAND ----------

# DBTITLE 1,create job watch schema and initial tables setup
spark.sql("CREATE SCHEMA IF NOT EXISTS job_watch")

spark.sql("""
CREATE TABLE IF NOT EXISTS job_watch.bronze_search_runs (
  run_id STRING,
  source STRING,
  fetched_at TIMESTAMP,
  query STRING,
  response_json STRING
)
""")

spark.sql("""
CREATE TABLE IF NOT EXISTS job_watch.silver_seek_results (
  source STRING,
  result_id STRING,
  title STRING,
  url STRING,
  content STRING,
  hourly_min DOUBLE,
  hourly_max DOUBLE,
  first_seen_at TIMESTAMP,
  last_seen_at TIMESTAMP
)
""")

spark.sql("""
CREATE TABLE IF NOT EXISTS job_watch.gold_seek_high_rate_roles (
  source STRING,
  result_id STRING,
  title STRING,
  url STRING,
  content STRING,
  hourly_min DOUBLE,
  hourly_max DOUBLE,
  last_seen_at TIMESTAMP
)
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## In-memory run buffers

# COMMAND ----------

# DBTITLE 1,initialize data storage for processing results
bronze_rows = []
silver_rows = []
errors = []
direct_warnings = []
rejected_rows = []
seen_canonical_urls = set()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Result normalisation/filter helper

# COMMAND ----------

# DBTITLE 1,process and filter payload for job results storage
def handle_payload(payload, source_name, allowed_domains, query):
    """Save raw payload to bronze buffer and accepted items to silver buffer."""
    bronze_rows.append({
        "run_id": RUN_ID,
        "source": source_name,
        "fetched_at": FETCHED_AT.isoformat(),
        "query": query,
        "response_json": json.dumps(payload),
    })

    accepted = 0

    for item in payload.get("results", []):
        title = item.get("title") or ""
        url = item.get("url") or ""
        content = item.get("content") or ""
        clean_url = canonicalize_url(url)

        reject_reason = None
        if not clean_url:
            reject_reason = "missing url"
        elif not url_allowed(clean_url, allowed_domains):
            reject_reason = "domain not allowed"
        elif clean_url in seen_canonical_urls:
            reject_reason = "duplicate url"
        else:
            is_job, reason = is_probably_job_result(source_name, clean_url, title, content)
            if not is_job:
                reject_reason = reason

        if reject_reason:
            rejected_rows.append({
                "source": source_name,
                "reason": reject_reason,
                "title": title,
                "url": clean_url,
                "content": content[:300],
            })
            continue

        seen_canonical_urls.add(clean_url)
        combined_text = f"{title}\n{content}\n{clean_url}"
        hourly_min, hourly_max = parse_hourly_rate(combined_text)

        silver_rows.append({
            "source": source_name,
            "result_id": make_result_id(clean_url, title),
            "title": title,
            "url": clean_url,
            "content": content,
            "hourly_min": hourly_min,
            "hourly_max": hourly_max,
            "first_seen_at": FETCHED_AT.isoformat(),
            "last_seen_at": FETCHED_AT.isoformat(),
        })
        accepted += 1

    return accepted

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch Bing RSS searches

# COMMAND ----------

# DBTITLE 1,search sources and handle query results with errors
for source_config in SEARCH_SOURCES:
    source_name = source_config["source"]
    allowed_domains = source_config.get("allowed_domains", [])

    for query in source_config.get("queries", []):
        print("=" * 100)
        print("SOURCE:", source_name)
        print("QUERY:", query)

        try:
            payload = source_search(source_config, query)
            accepted = handle_payload(payload, source_name, allowed_domains, query)

            print("RESULTS:", len(payload.get("results", [])))
            print("ACCEPTED:", accepted)
            print("FEED URL:", payload.get("feed_url"))

        except Exception as exc:
            msg = f"Failed source={source_name}, query={query}\n{exc}"
            print(msg)
            errors.append(msg)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch authorized direct HTML sources

# COMMAND ----------

# DBTITLE 1,execute direct URL scraping and handle results
if DIRECT_SCRAPE_ENABLED:
    for source_config in DIRECT_SOURCES:
        source_name = source_config["source"]
        allowed_domains = source_config.get("allowed_domains", [])

        for url in source_config.get("urls", []):
            print("=" * 100)
            print("SOURCE:", source_name)
            print("DIRECT URL:", url)

            try:
                payload = direct_html_search(source_config, url)
                accepted = handle_payload(payload, source_name, allowed_domains, url)

                print("RESULTS:", len(payload.get("results", [])))
                print("ACCEPTED:", accepted)

            except Exception as exc:
                msg = f"WARNING: Failed direct source={source_name}, url={url}\n{exc}"
                print(msg)
                direct_warnings.append(msg)
else:
    print("Direct scraping disabled")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch optional custom RSS feeds

# COMMAND ----------

# DBTITLE 1,fetch and process custom RSS feed data with error handl ...
for feed in CUSTOM_RSS_FEEDS:
    source_name = feed["source"]
    feed_url = feed["url"]
    allowed_domains = feed.get("allowed_domains", [])

    print("=" * 100)
    print("SOURCE:", source_name)
    print("CUSTOM RSS:", feed_url)

    try:
        payload = fetch_rss_url(feed_url, source_name, query=feed_url)
        accepted = handle_payload(payload, source_name, allowed_domains, feed_url)

        print("RESULTS:", len(payload.get("results", [])))
        print("ACCEPTED:", accepted)

    except Exception as exc:
        msg = f"Failed custom RSS source={source_name}, url={feed_url}\n{exc}"
        print(msg)
        errors.append(msg)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validate run and print rejected sample

# COMMAND ----------

# DBTITLE 1,validate data processing results and handle errors
print("=" * 100)
print("Bronze rows:", len(bronze_rows))
print("Silver rows:", len(silver_rows))
print("Rejected rows:", len(rejected_rows))
print("Errors:", len(errors))
print("Direct warnings:", len(direct_warnings))

if direct_warnings:
    print("Direct warning sample:")
    for warning in direct_warnings[:10]:
        print(warning)

print("Rejected sample:")
for row in rejected_rows[:20]:
    print(row)

if errors:
    raise RuntimeError("One or more sources failed:\n\n" + "\n\n".join(errors))
if not bronze_rows:
    raise RuntimeError("No bronze rows returned. No source returned usable responses.")
if not silver_rows:
    raise RuntimeError("No silver rows returned. Sources worked, but all rows were rejected.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Append bronze raw payloads

# COMMAND ----------

# DBTITLE 1,define bronze schema and save search runs data
bronze_schema = StructType([
    StructField("run_id", StringType()),
    StructField("source", StringType()),
    StructField("fetched_at", StringType()),
    StructField("query", StringType()),
    StructField("response_json", StringType()),
])

bronze_df = spark.createDataFrame(bronze_rows, bronze_schema).withColumn(
    "fetched_at", F.to_timestamp("fetched_at")
)

bronze_df.write.mode("append").saveAsTable("job_watch.bronze_search_runs")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Merge silver deduped results

# COMMAND ----------

# DBTITLE 1,update job watch results with new seek data
silver_schema = StructType([
    StructField("source", StringType()),
    StructField("result_id", StringType()),
    StructField("title", StringType()),
    StructField("url", StringType()),
    StructField("content", StringType()),
    StructField("hourly_min", DoubleType()),
    StructField("hourly_max", DoubleType()),
    StructField("first_seen_at", StringType()),
    StructField("last_seen_at", StringType()),
])

silver_df = (
    spark.createDataFrame(silver_rows, silver_schema)
    .dropDuplicates(["source", "result_id"])
    .withColumn("first_seen_at", F.to_timestamp("first_seen_at"))
    .withColumn("last_seen_at", F.to_timestamp("last_seen_at"))
)

silver_df.createOrReplaceTempView("new_seek_results")

spark.sql("""
MERGE INTO job_watch.silver_seek_results target
USING new_seek_results source
ON target.source = source.source
AND target.result_id = source.result_id
WHEN MATCHED THEN UPDATE SET
  target.title = source.title,
  target.url = source.url,
  target.content = source.content,
  target.hourly_min = source.hourly_min,
  target.hourly_max = source.hourly_max,
  target.last_seen_at = source.last_seen_at
WHEN NOT MATCHED THEN INSERT *
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Rebuild gold high-rate table

# COMMAND ----------

# DBTITLE 1,create high rate roles table from silver seek results
spark.sql(f"""
CREATE OR REPLACE TABLE job_watch.gold_seek_high_rate_roles AS
SELECT
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

# MAGIC %md
# MAGIC ## Display high-rate roles

# COMMAND ----------

# DBTITLE 1,fetch high rate job roles with hourly salary details
display(spark.sql("""
SELECT
  title,
  hourly_min,
  hourly_max,
  url,
  content,
  last_seen_at
FROM job_watch.gold_seek_high_rate_roles
ORDER BY hourly_max DESC, last_seen_at DESC
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display source summary

# COMMAND ----------

# DBTITLE 1,summarize job watch results by source and rate metrics
display(spark.sql("""
SELECT
  source,
  COUNT(*) AS total_rows,
  COUNT(hourly_max) AS rows_with_rate,
  MAX(hourly_max) AS max_rate
FROM job_watch.silver_seek_results
GROUP BY source
ORDER BY total_rows DESC
"""))
