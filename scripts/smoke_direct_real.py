from job_watch.config import DIRECT_SOURCES
from job_watch.direct_sources import ProtectionChallengeError, direct_html_search

source = DIRECT_SOURCES[0]
url = source["urls"][0]

try:
    payload = direct_html_search(source, url)
except ProtectionChallengeError as exc:
    # This is an expected, non-fatal result for protected sites. Do not bypass.
    print("WARNING: direct real smoke hit site protection challenge")
    print(f"url: {url}")
    print(f"error: {exc}")
except Exception as exc:
    # Direct scraping is warning-only in the Databricks notebook too.
    print("WARNING: direct real smoke could not fetch URL")
    print(f"url: {url}")
    print(f"error: {exc}")
else:
    print("url:", url)
    print("results:", len(payload["results"]))
    print("sample:", payload["results"][:3])
    assert "results" in payload
