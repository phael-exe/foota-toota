-- Official standings fact table (league tables across Tier 1 competitions).
-- Sourced from Football-Data.org API, unnested per team position. Clubs carry the canonical
-- team_id of silver.team_map, the one silver.matches uses; source_team_id and source_team_name
-- keep what Football-Data.org calls them.

CREATE OR REPLACE TABLE `PROJECT.silver.standings` AS
WITH unnested AS (
    SELECT
        _competition_code AS competition_code,
        _competition_name AS competition_name,
        JSON_VALUE(_season, '$.startDate') AS season_start_date,
        JSON_VALUE(_season, '$.endDate') AS season_end_date,
        SAFE_CAST(JSON_VALUE(_season, '$.currentMatchday') AS INT64) AS current_matchday,
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
    CASE u.competition_code
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
        ELSE LOWER(u.competition_code)
    END AS league_id,
    u.competition_code,
    competition_name,
    EXTRACT(YEAR FROM SAFE_CAST(season_start_date AS DATE)) AS season,
    rank,
    COALESCE(tm.team_id, u.team_id) AS team_id,
    COALESCE(tm.team_name, u.team_name) AS team_name,
    team_short_name,
    tm.tla AS team_tla,
    tm.crest_url AS team_crest_url,
    u.team_id AS source_team_id,
    u.team_name AS source_team_name,
    played,
    won,
    draw,
    lost,
    points,
    goals_for,
    goals_against,
    goal_difference,
    current_matchday,
    u.batch_id,
    u.source_file,
    u.ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM unnested u
LEFT JOIN `PROJECT.silver.team_map` tm
       ON tm.source_id = 'football_data_org' AND tm.raw_team_id = u.team_id;
