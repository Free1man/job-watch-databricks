"""Configuration for the job watcher."""

from __future__ import annotations

from .datasources.base import PayPeriod, Provider, SearchFilter
from .datasources.bing import BingDataSource
from .datasources.google import GoogleDataSource
from .datasources.indeed import IndeedDataSource
from .datasources.seek import SeekDataSource
from .datasources.trademe import TradeMeDataSource

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

ALL_DATA_SOURCES = (
    SeekDataSource(),
    TradeMeDataSource(),
    IndeedDataSource(),
    GoogleDataSource(),
    BingDataSource(),
)

DATA_SOURCES = (
    ALL_DATA_SOURCES
    if ENABLED_PROVIDERS is None
    else tuple(datasource for datasource in ALL_DATA_SOURCES if datasource.provider in ENABLED_PROVIDERS)
)
