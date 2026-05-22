"""Generic filtering helpers shared by datasources."""

from __future__ import annotations

from urllib.parse import urlparse


def url_allowed(url: str, allowed_domains: list[str] | tuple[str, ...]) -> bool:
    if not allowed_domains:
        return True
    host = urlparse(url).netloc.lower()
    return any(host == domain.lower() or host.endswith("." + domain.lower()) for domain in allowed_domains)
