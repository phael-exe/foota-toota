-- Materializes the Premier League history of Football-Data.co.uk into a native Bronze table.
CREATE OR REPLACE TABLE `PROJECT.bronze.football_data_uk_epl_historico` AS
SELECT
    *,
    '20261114' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_football_data_uk_epl_historico`;
