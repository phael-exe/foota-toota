-- Player market valuations time series fact table (656k+ valuation snapshots).
-- Sourced from Transfermarkt historical dataset.
-- Partitioned by date, clustered by player_id, current_club_id.

CREATE OR REPLACE TABLE `PROJECT.silver.player_valuations`
PARTITION BY valuation_date
CLUSTER BY player_id, current_club_id AS
SELECT
    SAFE_CAST(player_id AS INT64) AS player_id,
    SAFE_CAST(date AS DATE) AS valuation_date,
    SAFE_CAST(market_value_in_eur AS FLOAT64) AS market_value_eur,
    `PROJECT.silver.blank_to_null`(current_club_name) AS current_club_name,
    SAFE_CAST(current_club_id AS INT64) AS current_club_id,
    LOWER(`PROJECT.silver.blank_to_null`(player_club_domestic_competition_id)) AS competition_id,
    batch_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.transfermarkt_player_valuations`
WHERE `PROJECT.silver.blank_to_null`(player_id) IS NOT NULL
  AND `PROJECT.silver.blank_to_null`(date) IS NOT NULL;
