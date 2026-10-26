-- Materializes transfermarkt_players into a native Bronze table.
CREATE OR REPLACE TABLE `PROJECT.bronze.transfermarkt_players` AS
SELECT
    *,
    '20260923' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_transfermarkt_players`;
