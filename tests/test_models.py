from job_watch.datasources.base import Provider, infer_provider
from job_watch.models import normalize_raw_result


def test_infer_provider_from_source_and_url():
    assert infer_provider("trademe", "") == Provider.TRADEME
    assert infer_provider("anything", "https://www.seek.co.nz/job/123") == Provider.SEEK


def test_normalize_provider_payload_result():
    result = normalize_raw_result(
        {"source": "trademe", "provider": "trademe", "mode": "html"},
        {
            "title": "Developer",
            "url": "https://www.trademe.co.nz/a/jobs/it/programming-development/auckland/listing/1",
            "content": "Auckland",
        },
    )
    assert result.provider == "trademe"
    assert result.scrape_mode == "html"
    assert result.source == "trademe"
    assert result.title == "Developer"
    assert result.raw_json
