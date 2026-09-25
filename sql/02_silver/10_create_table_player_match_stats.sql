-- Per-player match statistics (77,991 = 78,006 - 15 exact duplicates).
-- S14: stats_json is unpacked with JSON_VALUE; rows holding invalid JSON are quarantined
--      by the silver checks (expected count: 0).
-- C2: these are statistics OF the match itself, so they can never be a pre-match attribute.
--     They are only valid as a label, as description, or aggregated over earlier matches.
CREATE OR REPLACE TABLE `PROJECT.silver.player_match_stats` AS
WITH deduplicated AS (
    SELECT DISTINCT
        `PROJECT.silver.blank_to_null`(match_id) AS match_id,
        `PROJECT.silver.blank_to_null`(team_id) AS team_id,
        `PROJECT.silver.blank_to_null`(team_name) AS team_name,
        `PROJECT.silver.blank_to_null`(player_id) AS player_id,
        `PROJECT.silver.blank_to_null`(player_name) AS player_name,
        `PROJECT.silver.blank_to_null`(position) AS position_raw,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(jersey_number) AS INT64) AS jersey_number,
        `PROJECT.silver.blank_to_null`(stats_json) AS stats_json
    FROM `PROJECT.bronze.stored_matches_stats_players`
)
SELECT
    d.match_id,
    d.team_id,
    d.team_name,
    d.player_id,
    d.player_name,
    d.position_raw,
    pm.canonical AS position,
    d.jersey_number,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.minutes.value')       AS INT64) AS minutes,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.goals.value')         AS INT64) AS goals,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.assists.value')       AS INT64) AS assists,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.shots_total.value')   AS INT64) AS shots_total,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.shots_on.value')      AS INT64) AS shots_on,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.passes_total.value')  AS INT64) AS passes_total,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.pass_accuracy.value') AS FLOAT64) AS pass_accuracy,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.yellow_cards.value')  AS INT64) AS yellow_cards,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.red_cards.value')     AS INT64) AS red_cards,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.rating.value') AS FLOAT64) AS rating,
    SAFE_CAST(JSON_VALUE(d.stats_json, '$.substitute.value')    AS BOOL) AS substitute,
    d.stats_json
FROM deduplicated d
LEFT JOIN `PROJECT.silver.position_map` pm
  ON pm.raw = d.position_raw;
