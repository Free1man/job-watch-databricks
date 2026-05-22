"""Configuration for the job watcher."""

from __future__ import annotations

from .datasources import PayPeriod, Provider, SearchFilter, enabled_datasources

MIN_RATE = 125

RSS_ENABLED = True
HTML_ENABLED = True
UI_ENABLED = False

# Use None for all registered providers, or a set like {Provider.SEEK, Provider.TRADEME}.
ENABLED_PROVIDERS: set[Provider] | None = None

# Optional site filters used by generic web-search providers such as Bing/Google.
SITE_FILTERS = ("seek.co.nz", "trademe.co.nz", "nz.indeed.com")

SEARCH_FILTER = SearchFilter(
    location="Auckland",
    contract_only=True,
    keywords=(
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
    ),
    min_rate=MIN_RATE,
    pay_period=PayPeriod.HOURLY,
)

SEARCH_CRITERIA = SEARCH_FILTER
DATA_SOURCES = enabled_datasources(ENABLED_PROVIDERS)
