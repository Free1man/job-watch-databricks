from job_watch.filters import url_allowed


def test_url_allowed_accepts_provider_domains_and_rejects_others():
    assert url_allowed("https://www.seek.co.nz/job/123", ["seek.co.nz"])
    assert url_allowed("https://jobs.seek.co.nz/job/123", ["seek.co.nz"])
    assert not url_allowed("https://evil.test/job/123", ["seek.co.nz"])
