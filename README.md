# seek-job-watch

Databricks Free Edition-friendly job monitor for Auckland contract software roles.

- First-class providers: `seek`, `trademe`, `indeed`, `google`, `bing`
- One shared `SearchFilter`: free-form keyword list, min/max rate, and pay period
- Providers explicitly declare support for `rss`, `html`, and `ui`
- Provider-specific query building, parsing, and filtering lives inside each datasource
- The Databricks notebook only calls providers and writes bronze/silver/gold tables
- No API keys

## Layout

- `notebooks/01_ingest_job_search.py` - Databricks ingest notebook source
- `notebooks/02_view_results.py` - Databricks results notebook source
- `notebooks/03_cleanup.py` - optional manual cleanup notebook
- `sql/migrations/` - versioned Databricks SQL schema/table migrations
- `sql/queries/` - reusable query/merge/report SQL assets
- `sql/migration_control/` - SQL used by the migration runner itself
- `sql/view_results.sql` - simple result queries
- `src/job_watch/config.py` - global provider/filter/mode config
- `src/job_watch/database.py` - shared Databricks table names, schemas, and SQL operations
- `src/job_watch/datasources/` - provider implementations
- `src/job_watch/direct_sources.py` - generic HTTP HTML fetch/link extraction helpers
- `src/job_watch/rss_sources.py` - generic RSS/Atom fetch/parsing helpers
- `src/job_watch/url_utils.py` - generic URL/domain helpers
- `src/job_watch/databricks_migrations.py` - migration runner used by the ingest notebook
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

SEARCH_FILTER = SearchFilter(
    keywords=("Auckland", "contract", "software developer", ...),
    min_rate=125,
    max_rate=None,
    pay_period=PayPeriod.HOURLY,
)
```

The notebook calls:

```python
payload = datasource.search(SEARCH_FILTER, site_filters=SITE_FILTERS)
```

`search()` is the wrapper. It runs only globally enabled and provider-supported implementations:

```python
supports_rss = True | False
supports_html = True | False
supports_ui = True | False
```

Each provider owns its implementation details:

```python
rss_search(search_filter, site_filters=())
html_search(search_filter, site_filters=())
ui_search(search_filter, site_filters=())
```

Current real-world HTML status:

- `trademe`: works with plain HTML fetch
- `seek`: blocked by site protection with plain HTML
- `indeed`: blocked by site protection with plain HTML
- `google` / `bing`: direct HTML search disallowed by robots.txt
- `ui`: disabled until a real browser renderer is implemented

All provider outputs are normalized into:

```text
provider, scrape_mode, source, result_id, title, url, content, published,
raw_json, hourly_min, hourly_max, first_seen_at, last_seen_at
```
