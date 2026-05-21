# seek-job-watch

Databricks Free Edition-friendly job monitor for Auckland software/development contract roles.

- Public Bing RSS search results as primary source
- Authorized direct HTML scraping enabled by default in `config.py`
- No API keys
- Bronze raw payloads, silver deduped results, gold high-rate roles

## Layout

- `notebooks/01_ingest_job_search.py` - Databricks notebook source
- `sql/view_results.sql` - simple result queries
- `src/job_watch/` - reusable parsing, RSS, config, and filters
- `tests/` - lightweight unit tests

## Local commands

Python-friendly commands are in `Makefile`:

```bash
make compile
make check
make test                 # dependency-free small test runner
make test-pytest          # optional, needs pytest installed
make smoke-direct-offline # no network
make smoke-rss            # hits Bing RSS
make smoke-direct-real    # hits allowlisted direct URL; may be blocked by robots.txt
make clean
```

Direct pytest command:

```bash
PYTHONPATH=src pytest
```

## Databricks

Import `notebooks/01_ingest_job_search.py` as a Databricks notebook or keep it in a Databricks Repo with this project. Run hourly as a job.

Direct scraping is controlled by:

```python
DIRECT_SCRAPE_ENABLED = True
DIRECT_SOURCES = [...]
```

Keep direct sources allowlisted, low-rate, and within your authorized testing scope.

Direct scraping failures are warnings only in the Databricks notebook. RSS/custom feed failures still fail the run.
