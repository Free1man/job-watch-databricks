SELECT
  provider,
  scrape_mode,
  source,
  COUNT(*) AS total_rows,
  COUNT(hourly_max) AS rows_with_rate,
  MAX(hourly_max) AS max_rate,
  MAX(last_seen_at) AS latest_seen_at
FROM ${silver_results_table}
GROUP BY provider, scrape_mode, source
ORDER BY total_rows DESC;
