-- Materializes football_data_org standings into a native Bronze table.
CREATE OR REPLACE TABLE `PROJECT.bronze.football_data_org_standings` AS
SELECT
    *,
    '20260923' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_football_data_org_standings`;
