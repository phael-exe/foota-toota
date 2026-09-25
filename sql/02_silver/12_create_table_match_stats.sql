-- Match stats fact table (shots, fouls, corners, cards).
-- Sourced from Football-Data.co.uk across 10 European leagues.

CREATE OR REPLACE TABLE `PROJECT.silver.match_stats` AS
SELECT
    CONCAT('fduk_', Div, '_', REGEXP_REPLACE(COALESCE(Date, ''), '[^0-9]', ''), '_',
           REGEXP_REPLACE(COALESCE(HomeTeam, ''), '[^a-zA-Z0-9]', ''), '_',
           REGEXP_REPLACE(COALESCE(AwayTeam, ''), '[^a-zA-Z0-9]', '')) AS match_id,
    SAFE_CAST(HS AS INT64) AS home_shots,
    SAFE_CAST(AS AS INT64) AS away_shots,
    SAFE_CAST(HST AS INT64) AS home_shots_on_target,
    SAFE_CAST(AST AS INT64) AS away_shots_on_target,
    SAFE_CAST(HF AS INT64) AS home_fouls,
    SAFE_CAST(AF AS INT64) AS away_fouls,
    SAFE_CAST(HC AS INT64) AS home_corners,
    SAFE_CAST(AC AS INT64) AS away_corners,
    SAFE_CAST(HY AS INT64) AS home_yellow_cards,
    SAFE_CAST(AY AS INT64) AS away_yellow_cards,
    SAFE_CAST(HR AS INT64) AS home_red_cards,
    SAFE_CAST(AR AS INT64) AS away_red_cards,
    Referee AS referee,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.football_data_uk`
WHERE HomeTeam IS NOT NULL AND AwayTeam IS NOT NULL;
