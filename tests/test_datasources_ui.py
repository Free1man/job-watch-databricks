from job_watch import config
from job_watch.datasources.bing import BingDataSource
from job_watch.datasources.google import GoogleDataSource
from job_watch.datasources.indeed import IndeedDataSource
from job_watch.datasources.seek import SeekDataSource
from job_watch.datasources.trademe import TradeMeDataSource
from job_watch.ui_sources import UiSearchNotImplemented


def _single_keyword_criteria():
    return config.SEARCH_CRITERIA.__class__(
        location=config.SEARCH_CRITERIA.location,
        contract_only=config.SEARCH_CRITERIA.contract_only,
        keywords=config.SEARCH_CRITERIA.keywords[:1],
        min_rate=config.SEARCH_CRITERIA.min_rate,
        max_rate=config.SEARCH_CRITERIA.max_rate,
        pay_period=config.SEARCH_CRITERIA.pay_period,
    )


def test_datasources_do_not_claim_ui_until_real_browser_renderer_exists():
    assert BingDataSource.supports_ui is False
    assert GoogleDataSource.supports_ui is False
    assert IndeedDataSource.supports_ui is False
    assert SeekDataSource.supports_ui is False
    assert TradeMeDataSource.supports_ui is False


def test_ui_enabled_does_not_run_for_unsupported_datasource(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", False)
    monkeypatch.setattr(config, "HTML_ENABLED", False)
    monkeypatch.setattr(config, "UI_ENABLED", True)

    payload = SeekDataSource().search(_single_keyword_criteria())

    assert payload["provider"] == "seek"
    assert payload["mode"] == "search"
    assert payload["modes"] == []
    assert payload["results"] == []


def test_default_ui_helper_is_explicitly_not_implemented():
    from job_watch.ui_sources import ui_search

    try:
        ui_search({"provider": "seek"}, "https://www.seek.co.nz/jobs")
    except UiSearchNotImplemented as exc:
        assert "provider=seek" in str(exc)
    else:
        raise AssertionError("ui_search should fail until a UI implementation is installed")
