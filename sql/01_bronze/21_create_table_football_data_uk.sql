-- Materializes football_data_uk into a native Bronze table with provenance stamps.
CREATE OR REPLACE TABLE `PROJECT.bronze.football_data_uk` AS
SELECT
    *,
    '20260923' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_football_data_uk`;
