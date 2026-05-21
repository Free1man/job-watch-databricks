"""Authorized, polite direct HTML scraping helpers.

This module is intentionally simple: allowlisted URLs only, no login/session use,
no CAPTCHA/protection bypass, no proxy rotation, and low request volume.
"""

from __future__ import annotations

import re
import time
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

USER_AGENT = "job-watch-authorized-scraper/1.0 (+personal research; contact: owner)"


class DirectFetchError(RuntimeError):
    """Base error for authorized direct fetch failures."""


class ProtectionChallengeError(DirectFetchError):
    """Raised when a site returns a bot-protection/challenge page.

    The project treats this as a stop sign: log it and fall back to RSS/search
    sources. Do not try to bypass CAPTCHA/Cloudflare/anti-bot controls.
    """


def looks_like_protection_challenge(status_code: int, body: str, headers: dict | None = None) -> bool:
    text = body[:5000].lower()
    server = ""
    if headers:
        server = headers.get("server", "").lower()

    challenge_markers = [
        "just a moment",
        "checking your browser",
        "challenge.cloudflare.com",
        "cf-chl",
        "captcha",
        "access denied",
        "bot detection",
    ]

    return (
        status_code in {403, 429, 503}
        and ("cloudflare" in server or any(marker in text for marker in challenge_markers))
    )


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []
        self.title = ""
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "a" and attrs_dict.get("href"):
            self._href = attrs_dict["href"]
            self._text_parts = []
        elif tag == "title":
            self._in_title = True
            self._title_parts = []

    def handle_data(self, data):
        if self._href is not None:
            self._text_parts.append(data)
        if self._in_title:
            self._title_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = " ".join(" ".join(self._text_parts).split())
            self.links.append({"href": self._href, "text": unescape(text)})
            self._href = None
            self._text_parts = []
        elif tag == "title" and self._in_title:
            self.title = " ".join(" ".join(self._title_parts).split())
            self._in_title = False


def _host_allowed(url: str, allowed_domains: list[str]) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == d.lower() or host.endswith("." + d.lower()) for d in allowed_domains)


def _robots_allowed(url: str, user_agent: str = USER_AGENT) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.read()
    return parser.can_fetch(user_agent, url)


def fetch_html_url(
    url: str,
    source_name: str,
    allowed_domains: list[str],
    respect_robots_txt: bool = True,
) -> str:
    if not _host_allowed(url, allowed_domains):
        raise DirectFetchError(f"Direct scrape URL is not in allowlist. source={source_name}, url={url}")

    if respect_robots_txt and not _robots_allowed(url):
        raise DirectFetchError(f"robots.txt disallows fetch. source={source_name}, url={url}")

    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        timeout=30,
    )

    if looks_like_protection_challenge(response.status_code, response.text, response.headers):
        raise ProtectionChallengeError(
            f"Direct scrape blocked by site protection. source={source_name}, "
            f"status={response.status_code}, url={url}, body={response.text[:1000]}"
        )

    if response.status_code >= 400:
        raise DirectFetchError(
            f"Direct scrape request failed. source={source_name}, status={response.status_code}, "
            f"url={url}, body={response.text[:1000]}"
        )

    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type and "text/plain" not in content_type:
        raise DirectFetchError(
            f"Direct scrape did not return HTML. source={source_name}, url={url}, "
            f"content_type={content_type}, body_start={response.text[:500]}"
        )

    return response.text


def extract_links_from_html(html: str, base_url: str, allowed_domains: list[str]) -> list[dict[str, str]]:
    parser = LinkParser()
    parser.feed(html)

    results = []
    seen = set()
    page_title = parser.title

    for link in parser.links:
        href = link.get("href") or ""
        text = link.get("text") or ""
        absolute_url = urljoin(base_url, href)
        if not _host_allowed(absolute_url, allowed_domains):
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)

        title = text or page_title or absolute_url
        results.append({
            "title": title,
            "url": absolute_url,
            "content": f"{page_title} {title}",
            "published": "",
        })

    return results


def direct_html_search(source_config: dict, url: str) -> dict:
    source_name = source_config["source"]
    allowed_domains = source_config.get("allowed_domains", [])
    respect_robots_txt = source_config.get("respect_robots_txt", True)
    delay_seconds = float(source_config.get("delay_seconds", 2.0))

    html = fetch_html_url(url, source_name, allowed_domains, respect_robots_txt)
    results = extract_links_from_html(html, url, allowed_domains)

    if delay_seconds > 0:
        time.sleep(delay_seconds)

    return {
        "source": source_name,
        "query": url,
        "feed_url": url,
        "raw_html_snippet": re.sub(r"\s+", " ", html[:5000]),
        "results": results,
    }
