"""Generic RSS/Atom parsing and fetching helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


def canonicalize_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    blocked_prefixes = ("utm_",)
    blocked_exact = {"tracking", "srsltid", "gclid", "fbclid", "rsqid"}
    clean_pairs = [
        (k, v)
        for k, v in query_pairs
        if not k.lower().startswith(blocked_prefixes) and k.lower() not in blocked_exact
    ]
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", urlencode(clean_pairs), ""))


def _child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return found.text
    return ""


ATOM_NS = "{http://www.w3.org/2005/Atom}"


def parse_rss_or_atom(xml_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    results: list[dict[str, str]] = []

    for item in root.findall(".//item"):
        results.append(
            {
                "title": item.findtext("title") or "",
                "url": item.findtext("link") or "",
                "content": item.findtext("description") or "",
                "published": item.findtext("pubDate") or "",
            }
        )

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        link = ""
        link_el = entry.find("atom:link", ns)
        if link_el is not None:
            link = link_el.attrib.get("href", "")
        results.append(
            {
                "title": _child_text(entry, (f"{ATOM_NS}title",)),
                "url": link,
                "content": _child_text(entry, (f"{ATOM_NS}summary", f"{ATOM_NS}content")),
                "published": _child_text(entry, (f"{ATOM_NS}published", f"{ATOM_NS}updated")),
            }
        )

    return results


def fetch_rss_url(feed_url: str, source_name: str, query: str = "") -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 job-watch-rss-monitor/1.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    response = requests.get(feed_url, headers=headers, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(
            f"RSS request failed. source={source_name}, status={response.status_code}, "
            f"query={query}, url={feed_url}, body={response.text[:1000]}"
        )

    text_start = response.text[:300].lower()
    if "<rss" not in text_start and "<?xml" not in text_start and "<feed" not in text_start:
        raise RuntimeError(
            f"RSS source did not return XML. source={source_name}, query={query}, "
            f"url={feed_url}, content_type={response.headers.get('content-type')}, "
            f"body_start={response.text[:500]}"
        )

    try:
        results = parse_rss_or_atom(response.content)
    except Exception as exc:
        raise RuntimeError(
            f"Could not parse RSS XML. source={source_name}, query={query}, "
            f"url={feed_url}, error={exc}, body_start={response.text[:500]}"
        ) from exc

    return {"source": source_name, "query": query, "feed_url": feed_url, "results": results}
