-- Official standings fact table (league tables across Tier 1 competitions).
-- Sourced from Football-Data.org API, unnested per team position.

CREATE OR REPLACE TABLE `PROJECT.silver.standings` AS
WITH unnested AS (
    SELECT
        JSON_VALUE(competition, '$.code') AS competition_code,
        JSON_VALUE(competition, '$.name') AS competition_name,
        JSON_VALUE(season, '$.startDate') AS season_start_date,
        JSON_VALUE(season, '$.endDate') AS season_end_date,
        SAFE_CAST(JSON_VALUE(season, '$.currentMatchday') AS INT64) AS current_matchday,
        SAFE_CAST(JSON_VALUE(entry, '$.position') AS INT64) AS rank,
        CAST(JSON_VALUE(entry, '$.team.id') AS STRING) AS team_id,
        JSON_VALUE(entry, '$.team.name') AS team_name,
        JSON_VALUE(entry, '$.team.shortName') AS team_short_name,
        SAFE_CAST(JSON_VALUE(entry, '$.playedGames') AS INT64) AS played,
        SAFE_CAST(JSON_VALUE(entry, '$.won') AS INT64) AS won,
        SAFE_CAST(JSON_VALUE(entry, '$.draw') AS INT64) AS draw,
        SAFE_CAST(JSON_VALUE(entry, '$.lost') AS INT64) AS lost,
        SAFE_CAST(JSON_VALUE(entry, '$.points') AS INT64) AS points,
        SAFE_CAST(JSON_VALUE(entry, '$.goalsFor') AS INT64) AS goals_for,
        SAFE_CAST(JSON_VALUE(entry, '$.goalsAgainst') AS INT64) AS goals_against,
        SAFE_CAST(JSON_VALUE(entry, '$.goalDifference') AS INT64) AS goal_difference,
        batch_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.football_data_org_standings`,
    UNNEST(JSON_EXTRACT_ARRAY(`table`)) AS entry
)
SELECT
    CASE competition_code
        WHEN 'PL'  THEN 'epl'
        WHEN 'BSA' THEN 'brasileirao_serie_a'
        WHEN 'PD'  THEN 'la_liga'
        WHEN 'BL1' THEN 'bundesliga'
        WHEN 'SA'  THEN 'serie_a'
        WHEN 'FL1' THEN 'ligue_1'
        WHEN 'CL'  THEN 'champions_league'
        WHEN 'ELC' THEN 'championship'
        WHEN 'DED' THEN 'eredivisie'
        WHEN 'PPL' THEN 'primeira_liga'
        ELSE LOWER(competition_code)
    END AS league_id,
    competition_code,
    competition_name,
    rank,
    team_id,
    team_name,
    team_short_name,
    played,
    won,
    draw,
    lost,
    points,
    goals_for,
    goals_against,
    goal_difference,
    current_matchday,
    batch_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM unnested;
