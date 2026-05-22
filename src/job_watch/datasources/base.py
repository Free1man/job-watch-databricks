"""Datasource interface and shared search filter metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..url_utils import domain_allowed


class Provider(str, Enum):
    SEEK = "seek"
    TRADEME = "trademe"
    INDEED = "indeed"
    BING = "bing"
    GOOGLE = "google"


class PayPeriod(str, Enum):
    HOURLY = "hourly"
    ANNUAL = "annual"


@dataclass(frozen=True)
class SearchFilter:
    keywords: tuple[str, ...]
    min_rate: float | None
    max_rate: float | None
    pay_period: PayPeriod

    def rate_terms(self) -> tuple[str, ...]:
        if self.min_rate is None:
            return ()
        values = [self.min_rate]
        if self.max_rate and self.max_rate != self.min_rate:
            values.append(self.max_rate)
        return tuple(f'"${int(value)}"' for value in values)

    def query_text(self) -> str:
        return " ".join(self.keywords)


SearchCriteria = SearchFilter


class DataSource:
    provider: Provider
    supports_rss = False
    supports_html = False
    supports_ui = False

    def rss_search(self, search_filter: SearchFilter, site_filters: tuple[str, ...] = ()) -> dict:
        raise NotImplementedError(f"{self.provider.value} does not support rss")

    def html_search(self, search_filter: SearchFilter, site_filters: tuple[str, ...] = ()) -> dict:
        raise NotImplementedError(f"{self.provider.value} does not support html")

    def ui_search(self, search_filter: SearchFilter, site_filters: tuple[str, ...] = ()) -> dict:
        raise NotImplementedError(f"{self.provider.value} does not support ui")

    def search(self, search_filter: SearchFilter, site_filters: tuple[str, ...] = ()) -> dict:
        from job_watch import config

        payloads = []
        if config.RSS_ENABLED and self.supports_rss:
            payloads.append(self.rss_search(search_filter, site_filters))
        if config.HTML_ENABLED and self.supports_html:
            payloads.append(self.html_search(search_filter, site_filters))
        if config.UI_ENABLED and self.supports_ui:
            payloads.append(self.ui_search(search_filter, site_filters))

        results = []
        for payload in payloads:
            mode = payload["mode"]
            for item in payload.get("results", []):
                results.append({**item, "mode": item.get("mode", mode)})

        return {
            "source": self.provider.value,
            "provider": self.provider.value,
            "mode": "search",
            "modes": [payload["mode"] for payload in payloads],
            "allowed_domains": self.allowed_domains_for(site_filters),
            "queries": [query for payload in payloads for query in payload.get("queries", [])],
            "feed_urls": [url for payload in payloads for url in payload.get("feed_urls", [])],
            "urls": [url for payload in payloads for url in payload.get("urls", [])],
            "results": results,
        }

    def allowed_domains_for(self, site_filters: tuple[str, ...] = ()) -> list[str]:
        return list(getattr(self, "allowed_domains", site_filters))

    def result_url_allowed(self, url: str) -> bool:
        return domain_allowed(url, self.allowed_domains_for())

    def result_allowed(self, item: dict, search_filter: SearchFilter) -> tuple[bool, str]:
        url = item.get("url") or ""
        if not url:
            return False, "missing url"
        if not self.result_url_allowed(url):
            return False, "domain not allowed"
        return True, "ok"

    def filter_payload(self, payload: dict, search_filter: SearchFilter) -> dict:
        accepted = []
        rejected = []
        for item in payload.get("results", []):
            ok, reason = self.result_allowed(item, search_filter)
            if ok:
                accepted.append(item)
            else:
                rejected.append({"reason": reason, "item": item})
        return {**payload, "results": accepted, "rejected": payload.get("rejected", []) + rejected}
