"""Datasource interface and shared search/filter metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from ..filters import url_allowed


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
    location: str = "Auckland"
    keywords: tuple[str, ...] = (
        "software developer",
        "software engineer",
        "senior developer",
        "senior software engineer",
        "full stack",
        "technical lead",
        "solution architect",
        "payments architect",
        ".NET",
        "AWS",
    )
    contract_only: bool = True
    min_rate: float | None = 125
    max_rate: float | None = None
    pay_period: PayPeriod = PayPeriod.HOURLY

    @property
    def contract_term(self) -> str:
        return "contract" if self.contract_only else ""

    def rate_terms(self) -> tuple[str, ...]:
        if self.min_rate is None:
            return ()
        if self.pay_period == PayPeriod.HOURLY:
            values = [self.min_rate]
            if self.max_rate and self.max_rate != self.min_rate:
                values.append(self.max_rate)
            return tuple(f'"${int(value)}"' for value in values)
        return (f'"${int(self.min_rate)}"',)

    def role_terms(self) -> tuple[str, ...]:
        terms = [keyword.lower() for keyword in self.keywords]
        terms.extend(("full-stack", "tech lead", "back end"))
        return tuple(dict.fromkeys(terms))


SearchCriteria = SearchFilter


class DataSource:
    provider: Provider
    supports_rss = False
    supports_html = False
    supports_ui = False
    blocked_terms: tuple[str, ...] = ()

    def rss_search(self, search_filter: SearchFilter, site_filters: tuple[str, ...] = ()) -> dict:
        raise NotImplementedError(f"{self.provider.value} does not support rss")

    def html_search(self, search_filter: SearchFilter, site_filters: tuple[str, ...] = ()) -> dict:
        raise NotImplementedError(f"{self.provider.value} does not support html")

    def ui_search(self, search_filter: SearchFilter, site_filters: tuple[str, ...] = ()) -> dict:
        raise NotImplementedError(f"{self.provider.value} does not support ui")

    def search(self, search_filter: SearchFilter, site_filters: tuple[str, ...] = ()) -> dict:
        """Wrapper: run enabled supported implementations and merge results."""
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
        return url_allowed(url, self.allowed_domains_for())

    def result_text_allowed(self, title: str, content: str, url: str, search_filter: SearchFilter) -> tuple[bool, str]:
        text = f"{title} {content} {url}".lower()
        location = search_filter.location.lower()
        if location and location not in text and location.replace(" ", "-") not in text:
            return False, f"missing location: {search_filter.location}"

        role_terms = search_filter.role_terms()
        if role_terms and not any(term in text for term in role_terms):
            return False, "missing role keyword"

        if any(term in text for term in self.blocked_terms):
            return False, "blocked provider term"

        return True, "ok"

    def result_allowed(self, item: dict, search_filter: SearchFilter) -> tuple[bool, str]:
        url = item.get("url") or ""
        title = item.get("title") or ""
        content = item.get("content") or ""
        if not url:
            return False, "missing url"
        if not self.result_url_allowed(url):
            return False, "domain not allowed"
        return self.result_text_allowed(title, content, url, search_filter)

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


def provider_from_value(value: Provider | str | None) -> Provider | None:
    if isinstance(value, Provider):
        return value
    if not value:
        return None
    try:
        return Provider(str(value))
    except ValueError:
        return None


PROVIDER_DOMAIN_HINTS: dict[Provider, tuple[str, ...]] = {
    Provider.SEEK: ("seek.co.nz", "nz.seek.com"),
    Provider.TRADEME: ("trademe.co.nz",),
    Provider.INDEED: ("indeed.com", "nz.indeed.com"),
    Provider.GOOGLE: ("google.",),
    Provider.BING: ("bing.",),
}


def infer_provider(source_name: str, url: str = "") -> Provider | None:
    source_lower = source_name.lower()
    host = urlparse(url).netloc.lower()

    for provider, hints in PROVIDER_DOMAIN_HINTS.items():
        if provider.value in source_lower:
            return provider
        if any(hint in host for hint in hints):
            return provider

    return None
