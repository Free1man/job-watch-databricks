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

# DBTITLE 1,bootstrap job watch imports
# MAGIC %run ./_bootstrap

# COMMAND ----------

# DBTITLE 1,import libraries and configure job watch environment
from collections import Counter
import json
import uuid
from datetime import datetime, timezone

from job_watch.config import DATA_SOURCES, MIN_RATE, SEARCH_CRITERIA, SITE_FILTERS
from job_watch.databricks_migrations import run_migrations
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
# MAGIC ## Apply database migrations
# MAGIC
# MAGIC Database structure is maintained in `sql/migrations/*.sql`.
# MAGIC Table names still use the old `seek` names until a later table migration.

# COMMAND ----------

# DBTITLE 1,apply job watch schema migrations
applied_migrations = run_migrations(spark)
print("Applied migrations:", applied_migrations)

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

# COMMAND ----------silver_merge_update_assignments

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
DB.append_bronze_rows(spark, bronze_rows)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Merge silver deduped results

# COMMAND ----------

# DBTITLE 1,update job watch results with new seek data
DB.merge_silver_rows(spark, silver_rows)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Rebuild gold high-rate table

# COMMAND ----------

# DBTITLE 1,create high rate roles table from silver seek results
DB.rebuild_gold_high_rate_roles(spark, MIN_RATE)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display high-rate roles

# COMMAND ----------

# DBTITLE 1,fetch high rate job roles with hourly salary details
display(DB.high_rate_roles_df(spark))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display source summary

# COMMAND ----------

# DBTITLE 1,summarize job watch results by source and rate metrics
display(DB.source_summary_df(spark))
