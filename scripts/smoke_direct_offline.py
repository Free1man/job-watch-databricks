from job_watch.direct_sources import extract_links_from_html
from job_watch.filters import is_probably_job_result

html = """
<html>
<head><title>Auckland jobs</title></head>
<body>
  <a href="/job/123">Senior Software Developer Auckland Contract</a>
  <a href="https://evil.test/x">Ignore me</a>
</body>
</html>
"""

results = extract_links_from_html(
    html,
    "https://www.seek.co.nz/search",
    ["seek.co.nz", "www.seek.co.nz"],
)

assert len(results) == 1, results
ok, reason = is_probably_job_result(
    "direct_seek",
    results[0]["url"],
    results[0]["title"],
    results[0]["content"],
)
assert ok, reason
print("offline direct smoke OK")
print(results[0])
