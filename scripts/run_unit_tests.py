"""Tiny dependency-free test runner for this small project.

Pytest is still supported if you install it, but this lets `make test` work on a
plain Python/Databricks-style environment.
"""

from tests.test_direct_sources import test_detects_cloudflare_challenge, test_normal_html_is_not_challenge
from tests.test_filters import test_accept_seek_job_result, test_reject_articles
from tests.test_parsing import test_parse_hourly_rate_examples


def main():
    tests = [
        test_parse_hourly_rate_examples,
        test_reject_articles,
        test_accept_seek_job_result,
        test_detects_cloudflare_challenge,
        test_normal_html_is_not_challenge,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"unit tests OK ({len(tests)} tests)")


if __name__ == "__main__":
    main()
