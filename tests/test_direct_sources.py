from job_watch.direct_sources import looks_like_protection_challenge


def test_detects_cloudflare_challenge():
    html = "<html><head><title>Just a moment...</title></head><body>challenge.cloudflare.com</body></html>"
    assert looks_like_protection_challenge(403, html, {"server": "cloudflare"})


def test_normal_html_is_not_challenge():
    html = "<html><head><title>Jobs</title></head><body><a href='/job/1'>Job</a></body></html>"
    assert not looks_like_protection_challenge(200, html, {})
