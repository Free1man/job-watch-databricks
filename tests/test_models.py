from job_watch.models import normalize_raw_result


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
