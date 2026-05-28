-- Upgrade older silver tables that were created before multi-provider support.
-- The migration runner treats duplicate-column/already-exists errors as already applied
-- so this can safely run against both old and current tables.

ALTER TABLE job_watch.silver_seek_results ADD COLUMNS (provider STRING);
ALTER TABLE job_watch.silver_seek_results ADD COLUMNS (scrape_mode STRING);
ALTER TABLE job_watch.silver_seek_results ADD COLUMNS (published STRING);
ALTER TABLE job_watch.silver_seek_results ADD COLUMNS (raw_json STRING);
