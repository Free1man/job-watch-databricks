SELECT
  provider,
  source,
  title,
  hourly_min,
  hourly_max,
  url,
  content,
  last_seen_at
FROM ${gold_high_rate_roles_table}
ORDER BY hourly_max DESC, last_seen_at DESC;
