INSERT INTO ${migrations_table}
SELECT '${migration_id}' AS migration_id, to_timestamp('${applied_at}') AS applied_at;
