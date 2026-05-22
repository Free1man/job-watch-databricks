from __future__ import annotations

from urllib.parse import urlencode

from .base import DataSource, Provider, SearchCriteria
from ..direct_sources import direct_html_search
from ..rss_sources import fetch_rss_url


class IndeedDataSource(DataSource):
    provider = Provider.INDEED
    supports_rss = True
    supports_html = False
    supports_ui = False
    allowed_domains = ("nz.indeed.com", "indeed.com")

    def queries(self, criteria: SearchCriteria) -> tuple[str, ...]:
        base_terms = [criteria.location]
        if criteria.contract_term:
            base_terms.append(criteria.contract_term)
        return tuple(f'site:nz.indeed.com {" ".join(base_terms)} "{keyword}"' for keyword in criteria.keywords[:4])

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

    def result_url_allowed(self, url: str) -> bool:
        return super().result_url_allowed(url) and "indeed.com" in url.lower()

    def urls(self, criteria: SearchCriteria) -> tuple[str, ...]:
        query = f'{criteria.keywords[0]} {criteria.contract_term}'.strip()
        return (
            "https://nz.indeed.com/jobs?" + urlencode({"q": query, "l": criteria.location}),
        )

    def html_search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        urls = self.urls(criteria)
        source_config = {
            "source": self.provider.value,
            "provider": self.provider.value,
            "mode": "html",
            "allowed_domains": list(self.allowed_domains),
            "respect_robots_txt": True,
            "delay_seconds": 2.0,
        }
        results = []
        for url in urls:
            payload = direct_html_search(source_config, url)
            results.extend(payload.get("results", []))
        return self.filter_payload({**source_config, "urls": list(urls), "results": results}, criteria)
