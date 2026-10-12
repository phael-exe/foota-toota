-- Materializes football_data_uk_bra into a native Bronze table with provenance stamps.
CREATE OR REPLACE TABLE `PROJECT.bronze.football_data_uk_bra` AS
SELECT
    *,
    '20261011' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_football_data_uk_bra`;
