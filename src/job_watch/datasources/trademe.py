from __future__ import annotations

import re
import time
from urllib.parse import quote_plus, urljoin, urlencode

from .base import DataSource, Provider, SearchCriteria
from ..direct_sources import LinkParser, fetch_html_url
from ..rss_sources import fetch_rss_url
from ..ui_sources import ui_search


class TradeMeDataSource(DataSource):
    provider = Provider.TRADEME
    supports_rss = True
    supports_html = True
    supports_ui = False
    allowed_domains = ("trademe.co.nz", "www.trademe.co.nz")

    def queries(self, criteria: SearchCriteria) -> tuple[str, ...]:
        query_text = criteria.query_text()
        queries = [f"site:trademe.co.nz/a/jobs {query_text}"]
        queries.extend(f"site:trademe.co.nz/a/jobs {query_text} {term}" for term in criteria.rate_terms())
        return tuple(queries)

    def urls(self, criteria: SearchCriteria) -> tuple[str, ...]:
        keywords_lower = {keyword.lower() for keyword in criteria.keywords}
        location_slug = "auckland" if "auckland" in keywords_lower else ""
        role_keywords = [keyword for keyword in criteria.keywords if keyword.lower() not in {"auckland", "contract"}]
        search_text = " ".join(role_keywords[:3])
        if "contract" in keywords_lower:
            search_text = f"{search_text} contract".strip()
        path = "https://www.trademe.co.nz/a/jobs/it/programming-development"
        if location_slug:
            path = f"{path}/{location_slug}"
        return (f"{path}/search?search_string={quote_plus(search_text)}", path)

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
        return super().result_url_allowed(url) and "trademe.co.nz" in url_lower and "/auckland/" in url_lower

    def clean_listing_title(self, title: str) -> str:
        title = re.sub(r"\s+", " ", title).strip()
        title = re.split(
            r"\s+(Listed\s+\w+|\d+\s+days?\s+ago|Be an early applicant|Quick apply|Job closes|Full-time|Part-time|Contract)\b",
            title,
        )[0]
        return title.strip()

    def extract_listing_links(self, html: str, base_url: str) -> list[dict[str, str]]:
        parser = LinkParser()
        parser.feed(html)
        results = []
        seen = set()
        for link in parser.links:
            absolute_url = urljoin(base_url, link.get("href") or "")
            if not re.search(r"/a/jobs/.+/listing/\d+", absolute_url):
                continue
            if absolute_url in seen:
                continue
            seen.add(absolute_url)
            title = self.clean_listing_title(link.get("text") or parser.title or absolute_url)
            results.append({"title": title, "url": absolute_url, "content": title, "published": ""})
        return results

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
            html = fetch_html_url(url, self.provider.value, list(self.allowed_domains), True)
            results.extend(self.extract_listing_links(html, url))
            if source_config["delay_seconds"] > 0:
                time.sleep(source_config["delay_seconds"])
        return self.filter_payload({**source_config, "urls": list(urls), "results": results}, criteria)

    def ui_search(self, criteria: SearchCriteria, site_filters: tuple[str, ...] = ()) -> dict:
        return self._search_urls(criteria, "ui", ui_search)
