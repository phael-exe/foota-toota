-- Materializes football_data_org matches into a native Bronze table.
CREATE OR REPLACE TABLE `PROJECT.bronze.football_data_org_matches` AS
SELECT
    *,
    '20260923' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_football_data_org_matches`;
