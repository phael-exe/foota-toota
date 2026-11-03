-- Players dimension.
-- Integrates BBD EPL squad players and Transfermarkt global player directory (50k+ players).
CREATE OR REPLACE TABLE `PROJECT.silver.players` AS
WITH bbd_players AS (
    SELECT
        `PROJECT.silver.blank_to_null`(id) AS player_id,
        `PROJECT.silver.blank_to_null`(team_id) AS team_id,
        `PROJECT.silver.blank_to_null`(name) AS player_name,
        CAST(NULL AS STRING) AS first_name,
        CAST(NULL AS STRING) AS last_name,
        CAST(NULL AS DATE) AS birth_date,
        `PROJECT.silver.blank_to_null`(position) AS position_raw,
        `PROJECT.silver.blank_to_null`(nationality) AS nationality,
        `PROJECT.silver.blank_to_null`(jersey_number) AS shirt_number,
        CAST(NULL AS INT64) AS height_cm,
        CAST(NULL AS STRING) AS preferred_foot,
        CAST(NULL AS FLOAT64) AS market_value_eur,
        CAST(NULL AS FLOAT64) AS highest_market_value_eur,
        `PROJECT.silver.blank_to_null`(headshot_url) AS photo_url,
        'bigballs' AS source_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.players`
),
tm_players AS (
    SELECT
        CAST(`PROJECT.silver.blank_to_null`(player_id) AS STRING) AS player_id,
        CAST(`PROJECT.silver.blank_to_null`(current_club_id) AS STRING) AS team_id,
        `PROJECT.silver.blank_to_null`(name) AS player_name,
        `PROJECT.silver.blank_to_null`(first_name) AS first_name,
        `PROJECT.silver.blank_to_null`(last_name) AS last_name,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(date_of_birth) AS DATE) AS birth_date,
        COALESCE(`PROJECT.silver.blank_to_null`(position), `PROJECT.silver.blank_to_null`(sub_position)) AS position_raw,
        COALESCE(`PROJECT.silver.blank_to_null`(country_of_citizenship), `PROJECT.silver.blank_to_null`(country_of_birth)) AS nationality,
        CAST(NULL AS STRING) AS shirt_number,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(height_in_cm) AS INT64) AS height_cm,
        `PROJECT.silver.blank_to_null`(foot) AS preferred_foot,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(market_value_in_eur) AS FLOAT64) AS market_value_eur,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(highest_market_value_in_eur) AS FLOAT64) AS highest_market_value_eur,
        `PROJECT.silver.blank_to_null`(image_url) AS photo_url,
        'transfermarkt' AS source_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.transfermarkt_players`
    WHERE `PROJECT.silver.blank_to_null`(player_id) IS NOT NULL
),
combined AS (
    SELECT * FROM bbd_players
    UNION ALL
    SELECT t.*
    FROM tm_players t
    WHERE NOT EXISTS (
        SELECT 1 FROM bbd_players b WHERE b.player_id = t.player_id
    )
)
SELECT
    player_id,
    team_id,
    player_name,
    first_name,
    last_name,
    birth_date,
    position_raw,
    nationality,
    shirt_number,
    height_cm,
    preferred_foot,
    market_value_eur,
    highest_market_value_eur,
    photo_url,
    source_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM combined;
