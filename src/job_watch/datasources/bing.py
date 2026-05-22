from __future__ import annotations

from urllib.parse import urlencode

from .base import DataSource, Provider, SearchCriteria
from ..direct_sources import direct_html_search
from ..rss_sources import fetch_rss_url


class BingDataSource(DataSource):
    provider = Provider.BING
    supports_rss = True
    supports_html = False
    supports_ui = False
    blocked_terms = (
        "nz herald",
        "nzherald",
        "rnz",
        "nucamp",
        "nzctu",
        "explainer",
        "employment relations amendment",
        "highest paying",
        "top 10",
        "news",
        "article",
        "blog",
        "bill 2025",
    )

    def allowed_domains_for(self, site_filters: tuple[str, ...] = ()) -> list[str]:
        return list(site_filters)

    def fetch_bing_rss(self, query: str) -> dict:
        feed_url = "https://www.bing.com/search?" + urlencode(
            {"q": query, "format": "rss", "cc": "NZ", "setmkt": "en-NZ"}
        )
        return fetch_rss_url(feed_url, self.provider.value, query)

    def rss_search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        base_terms = [criteria.location]
        if criteria.contract_term:
            base_terms.append(criteria.contract_term)

        site_prefixes = [f"site:{domain}" for domain in site_filters] or [""]
        queries = []
        for site_prefix in site_prefixes:
            prefix = f"{site_prefix} " if site_prefix else ""
            queries.extend(f'{prefix}{" ".join(base_terms)} "{keyword}"' for keyword in criteria.keywords)
            queries.extend(f"{prefix}{criteria.location} {term}" for term in criteria.rate_terms())

        results = []
        feed_urls = []
        for query in queries:
            payload = self.fetch_bing_rss(query)
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
        query = f'{criteria.location} {criteria.contract_term} "{criteria.keywords[0]}"'.strip()
        if site_filters:
            query = " OR ".join(f"site:{domain} {query}" for domain in site_filters)
        url = "https://www.bing.com/search?" + urlencode({"q": query, "cc": "NZ", "setmkt": "en-NZ"})
        source_config = {
            "source": self.provider.value,
            "provider": self.provider.value,
            "mode": "html",
            "allowed_domains": ["bing.com", "www.bing.com"],
            "respect_robots_txt": True,
            "delay_seconds": 2.0,
        }
        payload = direct_html_search(source_config, url)
        return self.filter_payload({**source_config, "urls": [url], "results": payload.get("results", [])}, criteria)
