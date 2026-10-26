-- Materializes transfermarkt_clubs into a native Bronze table.
CREATE OR REPLACE TABLE `PROJECT.bronze.transfermarkt_clubs` AS
SELECT
    *,
    '20260923' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_transfermarkt_clubs`;
