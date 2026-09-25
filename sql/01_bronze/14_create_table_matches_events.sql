-- Materializes the external table and stamps provenance on every row.
-- Static batch: batch_id = '20260908' (the day the CSVs were captured and uploaded).
CREATE OR REPLACE TABLE `PROJECT.bronze.matches_events` AS
SELECT
    *,
    '20260908' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    'gs://BUCKET/matches_events.csv' AS source_file
FROM `PROJECT.bronze.ext_matches_events`;
