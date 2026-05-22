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
from collections import Counter
import json
import os
import sys
import uuid
from datetime import datetime, timezone

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

# Make `src/job_watch` importable in Databricks Repos/Workspace files and local runs.
def _add_project_src_to_path():
    roots = []

    def add_root(path):
        if path and path not in roots:
            roots.append(path)

    add_root(os.getcwd())
    if "__file__" in globals():
        add_root(os.path.dirname(os.path.abspath(__file__)))

    try:
        notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        add_root(os.path.dirname("/Workspace" + notebook_path))
    except Exception:
        pass

    for root in list(roots):
        add_root(os.path.dirname(root))
        if os.path.basename(root) == "notebooks":
            add_root(os.path.dirname(root))

    for root in roots:
        candidate = os.path.abspath(os.path.join(root, "src"))
        if candidate not in sys.path and os.path.exists(os.path.join(candidate, "job_watch")):
            sys.path.insert(0, candidate)
            return


_add_project_src_to_path()

from job_watch.config import DATA_SOURCES, MIN_RATE, SEARCH_CRITERIA, SITE_FILTERS
from job_watch.url_utils import domain_allowed
from job_watch.models import normalize_raw_result
from job_watch.parsing import make_result_id, parse_hourly_rate
from job_watch.rss_sources import canonicalize_url

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
print("Providers:", [datasource.provider.value for datasource in DATA_SOURCES])
print("Site filters:", SITE_FILTERS)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Delta schema/tables
# MAGIC
# MAGIC Table names still use the old `seek` names until a later table migration.

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
USING DELTA
""")

spark.sql("""
CREATE TABLE IF NOT EXISTS job_watch.silver_seek_results (
  provider STRING,
  scrape_mode STRING,
  source STRING,
  result_id STRING,
  title STRING,
  url STRING,
  content STRING,
  published STRING,
  raw_json STRING,
  hourly_min DOUBLE,
  hourly_max DOUBLE,
  first_seen_at TIMESTAMP,
  last_seen_at TIMESTAMP
)
USING DELTA
""")

spark.sql("""
CREATE TABLE IF NOT EXISTS job_watch.gold_seek_high_rate_roles (
  provider STRING,
  scrape_mode STRING,
  source STRING,
  result_id STRING,
  title STRING,
  url STRING,
  content STRING,
  hourly_min DOUBLE,
  hourly_max DOUBLE,
  last_seen_at TIMESTAMP
)
USING DELTA
""")

# Upgrade older tables created before provider/scrape_mode columns existed.
for column_sql in [
    "provider STRING",
    "scrape_mode STRING",
    "published STRING",
    "raw_json STRING",
]:
    try:
        spark.sql(f"ALTER TABLE job_watch.silver_seek_results ADD COLUMNS ({column_sql})")
    except Exception as exc:
        message = str(exc).lower()
        if "already exists" not in message and "duplicate" not in message:
            print(f"Could not add silver column {column_sql}: {exc}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## In-memory run buffers

# COMMAND ----------

# DBTITLE 1,initialize data storage for processing results
bronze_rows = []
silver_rows = []
errors = []
provider_warnings = []
rejected_rows = []
seen_canonical_urls = set()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Result normalisation/filter helper

# COMMAND ----------

# DBTITLE 1,process and filter payload for job results storage
def handle_payload(payload, source_config, query):
    """Save raw payload to bronze buffer and accepted items to silver buffer."""
    source_name = source_config["source"]
    allowed_domains = source_config.get("allowed_domains", [])

    bronze_rows.append({
        "run_id": RUN_ID,
        "source": source_name,
        "fetched_at": FETCHED_AT.isoformat(),
        "query": query,
        "response_json": json.dumps(payload),
    })

    accepted = 0

    for item in payload.get("results", []):
        raw_result = normalize_raw_result(source_config, item)
        title = raw_result.title
        url = raw_result.url
        content = raw_result.content
        clean_url = canonicalize_url(url)

        reject_reason = None
        if not clean_url:
            reject_reason = "missing url"
        elif not domain_allowed(clean_url, allowed_domains):
            reject_reason = "domain not allowed"
        elif clean_url in seen_canonical_urls:
            reject_reason = "duplicate url"

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
            "provider": raw_result.provider,
            "scrape_mode": raw_result.scrape_mode,
            "source": source_name,
            "result_id": make_result_id(clean_url, title),
            "title": title,
            "url": clean_url,
            "content": content,
            "published": raw_result.published,
            "raw_json": raw_result.raw_json,
            "hourly_min": hourly_min,
            "hourly_max": hourly_max,
            "first_seen_at": FETCHED_AT.isoformat(),
            "last_seen_at": FETCHED_AT.isoformat(),
        })
        accepted += 1

    return accepted

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch providers

# COMMAND ----------

# DBTITLE 1,fetch each provider directly and handle normalized results
for datasource in DATA_SOURCES:
    provider_name = datasource.provider.value
    print("=" * 100)
    print("PROVIDER:", provider_name)

    try:
        payload = datasource.search(SEARCH_CRITERIA, site_filters=SITE_FILTERS)
        source_config = {
            "source": payload.get("source", provider_name),
            "provider": payload.get("provider", provider_name),
            "mode": payload.get("mode", "search"),
            "allowed_domains": payload.get("allowed_domains", []),
        }
        query = json.dumps({
            "queries": payload.get("queries", []),
            "urls": payload.get("urls", []),
            "site_filters": list(SITE_FILTERS),
        })
        accepted = handle_payload(payload, source_config, query)

        print("RESULTS:", len(payload.get("results", [])))
        print("ACCEPTED:", accepted)
        print("QUERIES:", payload.get("queries", []))
        print("URLS:", payload.get("urls", []))

    except Exception as exc:
        msg = f"WARNING: Failed provider={provider_name}\n{exc}"
        print(msg)
        provider_warnings.append(msg)

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
print("Provider warnings:", len(provider_warnings))

if provider_warnings:
    print("Provider warning sample:")
    for warning in provider_warnings[:10]:
        print(warning)

print("Rejected reasons:")
for reason, count in Counter(row["reason"] for row in rejected_rows).most_common():
    print(f"{reason}: {count}")

print("Rejected by source/reason:")
for (source, reason), count in Counter((row["source"], row["reason"]) for row in rejected_rows).most_common():
    print(f"{source} | {reason}: {count}")

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
    StructField("provider", StringType()),
    StructField("scrape_mode", StringType()),
    StructField("source", StringType()),
    StructField("result_id", StringType()),
    StructField("title", StringType()),
    StructField("url", StringType()),
    StructField("content", StringType()),
    StructField("published", StringType()),
    StructField("raw_json", StringType()),
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
  target.provider = source.provider,
  target.scrape_mode = source.scrape_mode,
  target.title = source.title,
  target.url = source.url,
  target.content = source.content,
  target.published = source.published,
  target.raw_json = source.raw_json,
  target.hourly_min = source.hourly_min,
  target.hourly_max = source.hourly_max,
  target.last_seen_at = source.last_seen_at
WHEN NOT MATCHED THEN INSERT (
  provider,
  scrape_mode,
  source,
  result_id,
  title,
  url,
  content,
  published,
  raw_json,
  hourly_min,
  hourly_max,
  first_seen_at,
  last_seen_at
) VALUES (
  source.provider,
  source.scrape_mode,
  source.source,
  source.result_id,
  source.title,
  source.url,
  source.content,
  source.published,
  source.raw_json,
  source.hourly_min,
  source.hourly_max,
  source.first_seen_at,
  source.last_seen_at
)
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Rebuild gold high-rate table

# COMMAND ----------

# DBTITLE 1,create high rate roles table from silver seek results
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

# MAGIC %md
# MAGIC ## Display high-rate roles

# COMMAND ----------

# DBTITLE 1,fetch high rate job roles with hourly salary details
display(spark.sql("""
SELECT
  provider,
  source,
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
  provider,
  scrape_mode,
  source,
  COUNT(*) AS total_rows,
  COUNT(hourly_max) AS rows_with_rate,
  MAX(hourly_max) AS max_rate
FROM job_watch.silver_seek_results
GROUP BY provider, scrape_mode, source
ORDER BY total_rows DESC
"""))
