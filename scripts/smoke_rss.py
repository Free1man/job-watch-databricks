from job_watch.config import SEARCH_SOURCES
from job_watch.rss_sources import source_search

source = SEARCH_SOURCES[0]
query = source["queries"][0]
payload = source_search(source, query)

print("feed:", payload["feed_url"])
print("results:", len(payload["results"]))
print("sample:", payload["results"][:2])
assert "results" in payload
