-- Materializes the upcoming-game odds into a native Bronze table, one row per game and snapshot.
-- snapshot_date comes from the dt= folder: the odds as they were on that day.
CREATE OR REPLACE TABLE `PROJECT.bronze.football_data_uk_fixtures` AS
SELECT
    *,
    PARSE_DATE('%Y-%m-%d', REGEXP_EXTRACT(_FILE_NAME, r'dt=(\d{4}-\d{2}-\d{2})')) AS snapshot_date,
    '20261114' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_football_data_uk_fixtures`;
