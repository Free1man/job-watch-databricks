from job_watch.parsing import parse_hourly_rate


def test_parse_hourly_rate_examples():
    assert parse_hourly_rate("$125/h") == (125.0, 125.0)
    assert parse_hourly_rate("$125 - $130/h") == (125.0, 130.0)
    assert parse_hourly_rate("$130-$135 + GST") == (130.0, 135.0)
    assert parse_hourly_rate("no rate") == (None, None)
