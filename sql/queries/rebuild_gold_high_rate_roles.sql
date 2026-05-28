CREATE OR REPLACE TABLE ${gold_high_rate_roles_table} AS
SELECT
${gold_select_columns}
FROM ${silver_results_table}
WHERE hourly_max >= ${min_rate}
ORDER BY hourly_max DESC, last_seen_at DESC;
