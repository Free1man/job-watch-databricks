"""Parsing helpers for job search result text."""

from __future__ import annotations

import hashlib
import re


def parse_hourly_rate(text: str | None) -> tuple[float | None, float | None]:
    """Extract likely hourly rate min/max from free text.

    Intentionally conservative: requires an hourly/context hint to avoid dates,
    job IDs, salaries, and unrelated numbers.
    """
    if not text:
        return None, None

    t = text.lower().replace(",", "")
    t = t.replace("nzd", "$")
    t = t.replace("per hour", "/h")
    t = t.replace("per hr", "/h")
    t = t.replace("an hour", "/h")
    t = t.replace("p/h", "/h")
    t = t.replace("ph", "/h")
    t = t.replace("–", "-").replace("—", "-")

    hourly_hint = any(
        hint in t
        for hint in ("/h", "/hr", "hour", "+ gst", "contract rate", "hourly rate")
    )
    if not hourly_hint:
        return None, None

    # Prefer explicit ranges near currency/hourly context.
    range_match = re.search(
        r"(?:\$\s*)?(\d{2,3}(?:\.\d+)?)\s*-\s*(?:\$\s*)?(\d{2,3}(?:\.\d+)?)\s*(?:/\s*h|/\s*hr|\+\s*gst|per\s+hour|hour)?",
        t,
    )
    if range_match:
        values = [float(range_match.group(1)), float(range_match.group(2))]
        values = [v for v in values if 50 <= v <= 300]
        if len(values) == 2:
            return min(values), max(values)

    nums = [float(n) for n in re.findall(r"\$?\s*(\d{2,3}(?:\.\d+)?)", t)]
    nums = [n for n in nums if 50 <= n <= 300]
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums[:2]), max(nums[:2])


def make_result_id(url: str, title: str) -> str:
    value = f"{url}|{title}".strip().lower()
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
