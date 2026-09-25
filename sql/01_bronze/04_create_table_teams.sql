-- Materializes the external table and stamps provenance on every row.
-- Static batch: batch_id = '20260908' (the day the CSVs were captured and uploaded).
CREATE OR REPLACE TABLE `PROJECT.bronze.teams` AS
SELECT
    *,
    '20260908' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    'gs://BUCKET/teams.csv' AS source_file
FROM `PROJECT.bronze.ext_teams`;
