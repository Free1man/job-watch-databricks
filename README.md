# seek-job-watch

Databricks Free Edition-friendly job monitor for Auckland software/development contract roles.

- First-class providers: `bing`, `google`, `seek`, `trademe`, `indeed`
- Each provider accepts the same `SearchCriteria` and optional `site_filters`
- Provider implementation details are internal: RSS/search/HTML are not exposed to the notebook
- No API keys
- Bronze raw payloads, silver deduped results, gold high-rate roles

## Layout

- `notebooks/01_ingest_job_search.py` - Databricks ingest notebook source
- `notebooks/02_view_results.py` - Databricks results notebook source
- `notebooks/03_cleanup.py` - optional manual cleanup notebook
- `sql/view_results.sql` - simple result queries
- `src/job_watch/datasources/` - provider implementations
- `src/job_watch/` - parsing, config, RSS/HTML helpers, and filters
- `tests/` - unit tests

## Local commands

```bash
make install-dev
make compile
make check
make test
make clean
```

Direct pytest command:

```bash
PYTHONPATH=src pytest
```

## Databricks

Import `notebooks/01_ingest_job_search.py` as a Databricks notebook or keep it in a Databricks Repo with this project. Run hourly as a job.

Provider config lives in `src/job_watch/config.py`:

```python
RSS_ENABLED = True
HTML_ENABLED = True
UI_ENABLED = False
ENABLED_PROVIDERS = None  # or {Provider.SEEK, Provider.TRADEME}
SITE_FILTERS = ("seek.co.nz", "trademe.co.nz", "nz.indeed.com")
SEARCH_CRITERIA = SearchCriteria(...)
DATA_SOURCES = enabled_datasources(ENABLED_PROVIDERS)
```

The notebook calls `datasource.search(SEARCH_CRITERIA, site_filters=SITE_FILTERS)`. The provider decides which enabled internals to run (`rss`, `html`, `ui`) and returns one normalized payload.

Each provider implements one interface:

```python
class DataSource:
    provider: Provider

    def search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        ...
```

All provider outputs are normalized into:

```text
provider, scrape_mode, source, result_id, title, url, content, published,
raw_json, hourly_min, hourly_max, first_seen_at, last_seen_at
```

Provider fetch failures are logged as warnings. The run fails only when no bronze or no accepted silver rows are produced.
