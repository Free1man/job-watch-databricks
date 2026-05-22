"""Consistent data shapes for datasource output and silver rows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RawResult:
    provider: str
    scrape_mode: str
    source: str
    title: str
    url: str
    content: str
    published: str = ""
    raw_json: str = "{}"

    def as_dict(self) -> dict:
        return asdict(self)


def normalize_raw_result(source_config: dict, item: dict) -> RawResult:
    source = source_config["source"]
    return RawResult(
        provider=source_config.get("provider") or source,
        scrape_mode=item.get("mode") or source_config.get("mode", "search"),
        source=source,
        title=item.get("title") or "",
        url=item.get("url") or "",
        content=item.get("content") or "",
        published=item.get("published") or "",
        raw_json=json.dumps(item, ensure_ascii=False, sort_keys=True),
    )
