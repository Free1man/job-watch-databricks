from __future__ import annotations

from urllib.parse import urlencode

from .base import DataSource, Provider, SearchCriteria
from ..direct_sources import direct_html_search
from ..rss_sources import fetch_rss_url
from ..ui_sources import ui_search


class SeekDataSource(DataSource):
    provider = Provider.SEEK
    supports_rss = True
    supports_html = True
    supports_ui = False
    allowed_domains = ("seek.co.nz", "www.seek.co.nz", "nz.seek.com")

    def queries(self, criteria: SearchCriteria) -> tuple[str, ...]:
        query_text = criteria.query_text()
        queries = [f"site:seek.co.nz/job {query_text}"]
        queries.extend(f"site:seek.co.nz/job {query_text} {term}" for term in criteria.rate_terms())
        return tuple(queries)

    def urls(self, criteria: SearchCriteria) -> tuple[str, ...]:
        keywords_lower = {keyword.lower() for keyword in criteria.keywords}
        location_slug = "All-Auckland" if "auckland" in keywords_lower else "All-New-Zealand"
        contract_part = "-contract" if "contract" in keywords_lower else ""
        role_keywords = [keyword for keyword in criteria.keywords if keyword.lower() not in {"auckland", "contract"}]
        urls = []
        for keyword in role_keywords[:3]:
            keyword_slug = keyword.lower().replace(".", "").replace(" ", "-")
            urls.append(f"https://www.seek.co.nz/{keyword_slug}{contract_part}-jobs/in-{location_slug}")
        return tuple(urls)

    def fetch_rss(self, query: str) -> dict:
        feed_url = "https://www.bing.com/search?" + urlencode(
            {"q": query, "format": "rss", "cc": "NZ", "setmkt": "en-NZ"}
        )
        return fetch_rss_url(feed_url, self.provider.value, query)

    def rss_search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        queries = self.queries(criteria)
        results = []
        feed_urls = []
        for query in queries:
            payload = self.fetch_rss(query)
            results.extend(payload.get("results", []))
            if payload.get("feed_url"):
                feed_urls.append(payload["feed_url"])
        return self.filter_payload({
            "source": self.provider.value,
            "provider": self.provider.value,
            "mode": "rss",
            "allowed_domains": list(self.allowed_domains),
            "queries": list(queries),
            "feed_urls": feed_urls,
            "results": results,
        }, criteria)

    def _search_urls(self, criteria: SearchCriteria, mode: str, fetch) -> dict:
        urls = self.urls(criteria)
        source_config = {
            "source": self.provider.value,
            "provider": self.provider.value,
            "mode": mode,
            "allowed_domains": list(self.allowed_domains),
            "respect_robots_txt": True,
            "delay_seconds": 2.0,
        }
        results = []
        for url in urls:
            payload = fetch(source_config, url)
            results.extend(payload.get("results", []))
        return self.filter_payload({**source_config, "urls": list(urls), "results": results}, criteria)

    def result_url_allowed(self, url: str) -> bool:
        url_lower = url.lower()
        return super().result_url_allowed(url) and (
            "/job/" in url_lower or "-jobs/in-" in url_lower or "/jobs/in-" in url_lower
        )

    def html_search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        return self._search_urls(criteria, "html", direct_html_search)

    def ui_search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        return self._search_urls(criteria, "ui", ui_search)
