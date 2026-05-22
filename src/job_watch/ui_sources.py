"""UI/browser based provider helpers.

The provider interface supports UI as a first-class implementation detail, but
this project does not ship a browser automation dependency yet. Providers can
call `ui_search`; tests monkeypatch it to validate provider wiring without
requiring Playwright/Selenium on Databricks.
"""

from __future__ import annotations


class UiSearchNotImplemented(RuntimeError):
    """Raised when a provider is asked to use UI fetching without an implementation."""


def ui_search(source_config: dict, url: str) -> dict:
    raise UiSearchNotImplemented(
        f"UI search is not implemented for provider={source_config.get('provider')} url={url}"
    )
