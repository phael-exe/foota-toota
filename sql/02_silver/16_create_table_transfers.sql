-- Player transfers fact table (175k+ historical player transfers).
-- Sourced from Transfermarkt historical dataset.
-- Partitioned by transfer_date, clustered by player_id, to_club_id.

CREATE OR REPLACE TABLE `PROJECT.silver.transfers`
PARTITION BY DATE_TRUNC(transfer_date, YEAR)
CLUSTER BY player_id, to_club_id AS
SELECT
    GENERATE_UUID() AS transfer_id,
    SAFE_CAST(player_id AS INT64) AS player_id,
    `PROJECT.silver.blank_to_null`(player_name) AS player_name,
    SAFE_CAST(transfer_date AS DATE) AS transfer_date,
    `PROJECT.silver.blank_to_null`(transfer_season) AS transfer_season,
    SAFE_CAST(from_club_id AS INT64) AS from_club_id,
    `PROJECT.silver.blank_to_null`(from_club_name) AS from_club_name,
    SAFE_CAST(to_club_id AS INT64) AS to_club_id,
    `PROJECT.silver.blank_to_null`(to_club_name) AS to_club_name,
    SAFE_CAST(transfer_fee AS FLOAT64) AS transfer_fee_eur,
    SAFE_CAST(market_value_in_eur AS FLOAT64) AS market_value_at_transfer_eur,
    batch_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.transfermarkt_transfers`
WHERE `PROJECT.silver.blank_to_null`(player_id) IS NOT NULL;
