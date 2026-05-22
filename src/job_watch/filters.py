"""Filtering helpers for public job-search results."""

from __future__ import annotations

from urllib.parse import urlparse

from .config import ROLE_KEYWORDS


def url_allowed(url: str, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return True
    host = urlparse(url).netloc.lower()
    return any(host == d.lower() or host.endswith("." + d.lower()) for d in allowed_domains)


def is_probably_job_result(source_name: str, url: str, title: str, content: str) -> tuple[bool, str]:
    text = f"{title} {content} {url}".lower()
    url_lower = url.lower()

    blocked_words = [
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
    ]
    if any(word in text for word in blocked_words):
        return False, "blocked article/news keyword"

    if "auckland" not in text and "all-auckland" not in text:
        return False, "missing auckland"

    if not any(keyword in text for keyword in ROLE_KEYWORDS):
        return False, "missing software/dev role keyword"

    if source_name in {"bing_seek", "direct_seek"} and not (
        "/job/" in url_lower or "-jobs/in-" in url_lower or "/jobs/in-" in url_lower
    ):
        return False, "seek url does not look like job/search result"
    if source_name in {"bing_trademe", "direct_trademe"} and "trademe.co.nz" not in url_lower:
        return False, "trademe url does not look valid"
    if source_name == "direct_trademe" and "/auckland/" not in url_lower:
        return False, "trademe direct result is not an Auckland listing URL"
    if source_name in {"bing_indeed", "direct_indeed"} and "indeed.com" not in url_lower:
        return False, "indeed url does not look valid"
    if source_name == "bing_jobs_govt_nz" and "jobs.govt.nz" not in url_lower:
        return False, "jobs.govt.nz url does not look valid"

    return True, "ok"
