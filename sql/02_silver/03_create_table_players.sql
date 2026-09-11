-- Players. Dropped: full_name, display_name, date_of_birth, height*, weight* (100% empty);
-- league_name and sport are constant across the batch.
CREATE OR REPLACE TABLE `PROJECT.silver.players` AS
SELECT
    `PROJECT.silver.blank_to_null`(id) AS player_id,
    `PROJECT.silver.blank_to_null`(name) AS name,
    `PROJECT.silver.blank_to_null`(position) AS position,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(jersey_number) AS INT64) AS jersey_number,
    `PROJECT.silver.blank_to_null`(nationality) AS nationality,
    `PROJECT.silver.blank_to_null`(team_id) AS team_id,
    `PROJECT.silver.blank_to_null`(headshot_url) AS headshot_url,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.players`;
