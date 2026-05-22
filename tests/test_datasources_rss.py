from job_watch import config
from job_watch.datasources.bing import BingDataSource
from job_watch.datasources.google import GoogleDataSource
from job_watch.datasources.indeed import IndeedDataSource
from job_watch.datasources.seek import SeekDataSource
from job_watch.datasources.trademe import TradeMeDataSource


def _single_keyword_criteria():
    return config.SEARCH_CRITERIA.__class__(
        location=config.SEARCH_CRITERIA.location,
        contract_only=config.SEARCH_CRITERIA.contract_only,
        keywords=config.SEARCH_CRITERIA.keywords[:1],
        min_rate=config.SEARCH_CRITERIA.min_rate,
        max_rate=config.SEARCH_CRITERIA.max_rate,
        pay_period=config.SEARCH_CRITERIA.pay_period,
    )


def test_datasources_declare_rss_support_explicitly():
    assert BingDataSource.supports_rss is True
    assert GoogleDataSource.supports_rss is True
    assert IndeedDataSource.supports_rss is True
    assert SeekDataSource.supports_rss is True
    assert TradeMeDataSource.supports_rss is True


def test_bing_search_runs_rss_when_global_rss_enabled(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", True)
    monkeypatch.setattr(config, "HTML_ENABLED", False)
    monkeypatch.setattr(config, "UI_ENABLED", False)
    calls = []

    def fake_fetch(self, query):
        calls.append((query, self.provider.value))
        return {"feed_url": "https://www.bing.com/search?format=rss", "results": [{"title": "Developer", "url": "https://www.seek.co.nz/job/1", "content": "Auckland software developer"}]}

    monkeypatch.setattr(BingDataSource, "fetch_bing_rss", fake_fetch)

    payload = BingDataSource().search(_single_keyword_criteria(), site_filters=("seek.co.nz",))

    assert payload["provider"] == "bing"
    assert payload["mode"] == "search"
    assert payload["modes"] == ["rss"]
    assert payload["allowed_domains"] == ["seek.co.nz"]
    assert payload["results"]
    assert calls
    assert all("site:seek.co.nz" in query for query, _ in calls)


def test_google_search_runs_rss_when_global_rss_enabled(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", True)
    monkeypatch.setattr(config, "HTML_ENABLED", False)
    monkeypatch.setattr(config, "UI_ENABLED", False)
    calls = []

    def fake_fetch(self, query):
        calls.append((query, self.provider.value))
        return {"feed_url": "https://news.google.com/rss/search", "results": []}

    monkeypatch.setattr(GoogleDataSource, "fetch_google_news_rss", fake_fetch)

    payload = GoogleDataSource().search(_single_keyword_criteria(), site_filters=("trademe.co.nz",))

    assert payload["provider"] == "google"
    assert payload["mode"] == "search"
    assert payload["modes"] == ["rss"]
    assert payload["allowed_domains"] == ["trademe.co.nz"]
    assert calls
    assert all("site:trademe.co.nz" in query for query, _ in calls)


def test_indeed_search_runs_rss_when_global_rss_enabled(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", True)
    monkeypatch.setattr(config, "HTML_ENABLED", False)
    monkeypatch.setattr(config, "UI_ENABLED", False)
    calls = []

    def fake_fetch(self, query):
        calls.append((query, self.provider.value))
        return {"feed_url": "https://www.bing.com/search?format=rss", "results": [{"title": "Developer", "url": "https://nz.indeed.com/viewjob?jk=1", "content": "Auckland software developer"}]}

    monkeypatch.setattr(IndeedDataSource, "fetch_rss", fake_fetch)

    payload = IndeedDataSource().search(_single_keyword_criteria())

    assert payload["provider"] == "indeed"
    assert payload["mode"] == "search"
    assert payload["modes"] == ["rss"]
    assert payload["results"]
    assert calls
    assert all(source_name == "indeed" for _, source_name in calls)


def test_seek_search_runs_rss_when_global_rss_enabled(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", True)
    monkeypatch.setattr(config, "HTML_ENABLED", False)
    monkeypatch.setattr(config, "UI_ENABLED", False)
    calls = []

    def fake_fetch(self, query):
        calls.append((query, self.provider.value))
        return {"feed_url": "https://www.bing.com/search?format=rss", "results": []}

    monkeypatch.setattr(SeekDataSource, "fetch_rss", fake_fetch)

    payload = SeekDataSource().search(_single_keyword_criteria())

    assert payload["provider"] == "seek"
    assert payload["modes"] == ["rss"]
    assert calls
    assert all("site:seek.co.nz/job" in query for query, _ in calls)
    assert all(source_name == "seek" for _, source_name in calls)


def test_trademe_search_runs_rss_when_global_rss_enabled(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", True)
    monkeypatch.setattr(config, "HTML_ENABLED", False)
    monkeypatch.setattr(config, "UI_ENABLED", False)
    calls = []

    def fake_fetch(self, query):
        calls.append((query, self.provider.value))
        return {"feed_url": "https://www.bing.com/search?format=rss", "results": []}

    monkeypatch.setattr(TradeMeDataSource, "fetch_rss", fake_fetch)

    payload = TradeMeDataSource().search(_single_keyword_criteria())

    assert payload["provider"] == "trademe"
    assert payload["modes"] == ["rss"]
    assert calls
    assert all("site:trademe.co.nz/a/jobs" in query for query, _ in calls)
    assert all(source_name == "trademe" for _, source_name in calls)


def test_rss_disabled_means_search_does_not_run_rss(monkeypatch):
    monkeypatch.setattr(config, "RSS_ENABLED", False)
    monkeypatch.setattr(config, "HTML_ENABLED", False)
    monkeypatch.setattr(config, "UI_ENABLED", False)

    payload = BingDataSource().search(_single_keyword_criteria(), site_filters=("seek.co.nz",))

    assert payload["provider"] == "bing"
    assert payload["mode"] == "search"
    assert payload["modes"] == []
    assert payload["results"] == []
