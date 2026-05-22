from job_watch.url_utils import domain_allowed


def test_domain_allowed_accepts_configured_domains_and_subdomains():
    assert domain_allowed("https://www.seek.co.nz/job/123", ["seek.co.nz"])
    assert domain_allowed("https://jobs.seek.co.nz/job/123", ["seek.co.nz"])
    assert not domain_allowed("https://evil.test/job/123", ["seek.co.nz"])
