CREATE TABLE IF NOT EXISTS ${migrations_table} (
  migration_id STRING,
  applied_at TIMESTAMP
)
USING DELTA;
