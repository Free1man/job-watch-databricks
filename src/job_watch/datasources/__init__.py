from __future__ import annotations

from .base import DataSource, PayPeriod, Provider, SearchCriteria, SearchFilter, infer_provider
from .bing import BingDataSource
from .google import GoogleDataSource
from .indeed import IndeedDataSource
from .seek import SeekDataSource
from .trademe import TradeMeDataSource

DATA_SOURCES: tuple[DataSource, ...] = (
    SeekDataSource(),
    TradeMeDataSource(),
    IndeedDataSource(),
    GoogleDataSource(),
    BingDataSource(),
)


def enabled_datasources(enabled_providers: set[Provider] | None = None) -> tuple[DataSource, ...]:
    if enabled_providers is None:
        return DATA_SOURCES
    return tuple(datasource for datasource in DATA_SOURCES if datasource.provider in enabled_providers)


__all__ = [
    "DATA_SOURCES",
    "BingDataSource",
    "DataSource",
    "GoogleDataSource",
    "IndeedDataSource",
    "PayPeriod",
    "Provider",
    "SearchCriteria",
    "SearchFilter",
    "SeekDataSource",
    "TradeMeDataSource",
    "enabled_datasources",
    "infer_provider",
]
