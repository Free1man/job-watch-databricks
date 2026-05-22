from __future__ import annotations

from urllib.parse import urlencode

from .base import DataSource, Provider, SearchCriteria
from ..direct_sources import direct_html_search
from ..rss_sources import fetch_rss_url


class GoogleDataSource(DataSource):
    provider = Provider.GOOGLE
    supports_rss = True
    supports_html = False
    supports_ui = False
    def allowed_domains_for(self, site_filters: tuple[str, ...] = ()) -> list[str]:
        return list(site_filters)

    def fetch_google_news_rss(self, query: str) -> dict:
        feed_url = "https://news.google.com/rss/search?" + urlencode(
            {"q": query, "hl": "en-NZ", "gl": "NZ", "ceid": "NZ:en"}
        )
        return fetch_rss_url(feed_url, self.provider.value, query)

    def rss_search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        query_text = criteria.query_text()
        site_prefixes = [f"site:{domain}" for domain in site_filters] or [""]
        queries = []
        for site_prefix in site_prefixes:
            prefix = f"{site_prefix} " if site_prefix else ""
            queries.append(f"{prefix}{query_text}".strip())
            queries.extend(f"{prefix}{query_text} {term}".strip() for term in criteria.rate_terms())

        results = []
        feed_urls = []
        for query in queries:
            payload = self.fetch_google_news_rss(query)
            results.extend(payload.get("results", []))
            if payload.get("feed_url"):
                feed_urls.append(payload["feed_url"])

        return self.filter_payload({
            "source": self.provider.value,
            "provider": self.provider.value,
            "mode": "rss",
            "allowed_domains": list(site_filters),
            "queries": queries,
            "feed_urls": feed_urls,
            "results": results,
        }, criteria)

    def html_search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        query = criteria.query_text()
        if site_filters:
            query = " OR ".join(f"site:{domain} {query}" for domain in site_filters)
        url = "https://www.google.com/search?" + urlencode({"q": query, "hl": "en-NZ", "gl": "NZ"})
        source_config = {
            "source": self.provider.value,
            "provider": self.provider.value,
            "mode": "html",
            "allowed_domains": ["google.com", "www.google.com"],
            "respect_robots_txt": True,
            "delay_seconds": 2.0,
        }
        payload = direct_html_search(source_config, url)
        return self.filter_payload({**source_config, "urls": [url], "results": payload.get("results", [])}, criteria)
