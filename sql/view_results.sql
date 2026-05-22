SELECT
  provider,
  scrape_mode,
  source,
  title,
  hourly_min,
  hourly_max,
  url,
  content,
  last_seen_at
FROM job_watch.gold_seek_high_rate_roles
ORDER BY hourly_max DESC, last_seen_at DESC;
