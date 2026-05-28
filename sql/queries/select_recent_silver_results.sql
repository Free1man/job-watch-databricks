SELECT
${recent_silver_select_columns}
FROM ${silver_results_table}
ORDER BY last_seen_at DESC
LIMIT ${limit};
