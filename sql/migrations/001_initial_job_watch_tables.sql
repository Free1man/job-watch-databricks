-- Initial job_watch schema and Delta tables.
-- Table names currently keep the historical `seek` suffix for compatibility.

CREATE SCHEMA IF NOT EXISTS job_watch;

CREATE TABLE IF NOT EXISTS job_watch.bronze_search_runs (
  run_id STRING,
  source STRING,
  fetched_at TIMESTAMP,
  query STRING,
  response_json STRING
)
USING DELTA;

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
USING DELTA;

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
USING DELTA;
