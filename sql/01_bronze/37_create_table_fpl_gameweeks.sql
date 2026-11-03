-- Materializes fpl_gameweeks into a native Bronze table.
CREATE OR REPLACE TABLE `PROJECT.bronze.fpl_gameweeks` AS
SELECT
    *,
    '20260923' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_fpl_gameweeks`;
