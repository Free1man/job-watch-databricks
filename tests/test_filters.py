from job_watch.filters import is_probably_job_result, url_allowed


def test_reject_articles():
    cases = [
        ("bing_seek", "https://www.nzherald.co.nz/business/story", "NZ Herald article", "Auckland software developer market news"),
        ("bing_seek", "https://www.rnz.co.nz/news/business/123", "RNZ article", "Auckland software engineer news"),
        ("bing_seek", "https://www.nucamp.co/blog/top-10", "Nucamp article", "Auckland software developer top 10"),
    ]
    for source, url, title, content in cases:
        ok, reason = is_probably_job_result(source, url, title, content)
        assert not ok, reason


def test_accept_seek_job_result():
    url = "https://www.seek.co.nz/job/123456"
    title = "Senior Software Developer - Contract"
    content = "Auckland CBD contract software developer role."
    assert url_allowed(url, ["seek.co.nz", "www.seek.co.nz"])
    assert is_probably_job_result("bing_seek", url, title, content) == (True, "ok")
