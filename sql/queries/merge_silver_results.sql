MERGE INTO ${silver_results_table} target
USING ${new_results_view} source
ON target.source = source.source
AND target.result_id = source.result_id
WHEN MATCHED THEN UPDATE SET
${silver_merge_update_assignments}
WHEN NOT MATCHED THEN INSERT (
${silver_insert_columns}
) VALUES (
${silver_insert_values}
);
