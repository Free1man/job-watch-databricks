from job_watch import config
from job_watch.datasources.seek import SeekDataSource
from job_watch.datasources.trademe import TradeMeDataSource
from job_watch.filters import url_allowed
from job_watch.models import normalize_raw_result
from job_watch.rss_sources import canonicalize_url


def _single_keyword_criteria():
    return config.SEARCH_CRITERIA.__class__(
        location=config.SEARCH_CRITERIA.location,
        contract_only=config.SEARCH_CRITERIA.contract_only,
        keywords=config.SEARCH_CRITERIA.keywords[:1],
        min_rate=config.SEARCH_CRITERIA.min_rate,
        max_rate=config.SEARCH_CRITERIA.max_rate,
        pay_period=config.SEARCH_CRITERIA.pay_period,
    )


def _assert_accepted_provider_result(payload: dict, expected_mode: str):
    raw = normalize_raw_result(payload, payload["results"][0])
    clean_url = canonicalize_url(raw.url)

    assert raw.provider == payload["provider"]
    assert raw.source == payload["source"]
    assert raw.scrape_mode == expected_mode
    assert url_allowed(clean_url, payload["allowed_domains"])


def test_seek_declares_html_support():
    assert SeekDataSource.supports_html is True


def test_trademe_declares_html_support():
    assert TradeMeDataSource.supports_html is True


def test_seek_search_runs_html_when_global_html_enabled(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", False)
    monkeypatch.setattr(config, "HTML_ENABLED", True)
    monkeypatch.setattr(config, "UI_ENABLED", False)
    fetched_urls = []

    def fake_direct_html_search(source_config, url):
        fetched_urls.append(url)
        assert source_config["mode"] == "html"
        return {
            "results": [
                {
                    "title": "Senior Software Developer Contract",
                    "url": "https://www.seek.co.nz/job/123",
                    "content": "Auckland CBD contract software developer $125/h",
                }
            ]
        }

    monkeypatch.setattr("job_watch.datasources.seek.direct_html_search", fake_direct_html_search)

    payload = SeekDataSource().search(_single_keyword_criteria())

    assert payload["provider"] == "seek"
    assert payload["mode"] == "search"
    assert payload["modes"] == ["html"]
    assert fetched_urls == payload["urls"]
    _assert_accepted_provider_result(payload, "html")


def test_trademe_search_runs_html_when_global_html_enabled(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", False)
    monkeypatch.setattr(config, "HTML_ENABLED", True)
    monkeypatch.setattr(config, "UI_ENABLED", False)
    fetched_urls = []

    def fake_fetch_html_url(url, source_name, allowed_domains, respect_robots_txt=True):
        fetched_urls.append(url)
        return """
        <html><head><title>Trade Me Jobs</title></head><body>
          <a href="/a/jobs/it/programming-development/auckland/listing/123">
            Senior Software Developer Contract Listed today
          </a>
        </body></html>
        """

    monkeypatch.setattr("job_watch.datasources.trademe.fetch_html_url", fake_fetch_html_url)

    payload = TradeMeDataSource().search(_single_keyword_criteria())

    assert payload["provider"] == "trademe"
    assert payload["mode"] == "search"
    assert payload["modes"] == ["html"]
    assert fetched_urls == payload["urls"]
    _assert_accepted_provider_result(payload, "html")


def test_html_disabled_means_search_does_not_run_html(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", False)
    monkeypatch.setattr(config, "HTML_ENABLED", False)
    monkeypatch.setattr(config, "UI_ENABLED", False)

    payload = SeekDataSource().search(_single_keyword_criteria())

    assert payload["provider"] == "seek"
    assert payload["mode"] == "search"
    assert payload["modes"] == []
    assert payload["results"] == []
