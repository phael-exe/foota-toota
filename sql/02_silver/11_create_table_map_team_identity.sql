-- Team identity resolution map (De-Para).
-- Maps variations in club names across sources (BBD, Football-Data UK, Football-Data.org,
-- Brasileirao, Transfermarkt, FPL) to canonical team IDs and names.

CREATE OR REPLACE TABLE `PROJECT.silver.map_team_identity` AS
WITH all_names AS (
    -- Transfermarkt clubs as primary canonical spine
    SELECT
        CAST(club_id AS STRING) AS canonical_team_id,
        name AS canonical_team_name,
        name AS raw_team_name,
        'transfermarkt' AS source_id
    FROM `PROJECT.bronze.transfermarkt_clubs`
    UNION ALL
    -- BBD teams
    SELECT
        id AS canonical_team_id,
        name AS canonical_team_name,
        name AS raw_team_name,
        'bigballs' AS source_id
    FROM `PROJECT.bronze.teams`
    UNION ALL
    -- Football-Data UK Home Teams
    SELECT
        HomeTeam AS canonical_team_id,
        HomeTeam AS canonical_team_name,
        HomeTeam AS raw_team_name,
        'football_data_uk' AS source_id
    FROM `PROJECT.bronze.football_data_uk`
    WHERE HomeTeam IS NOT NULL
    UNION ALL
    -- Brasileirao Home Teams
    SELECT
        mandante AS canonical_team_id,
        mandante AS canonical_team_name,
        mandante AS raw_team_name,
        'brasileirao_historico' AS source_id
    FROM `PROJECT.bronze.brasileirao_historico`
    WHERE mandante IS NOT NULL
)
SELECT DISTINCT
    canonical_team_id,
    canonical_team_name,
    raw_team_name,
    LOWER(REGEXP_REPLACE(NORMALIZE(raw_team_name, NFD), r'\pM', '')) AS normalized_clean_name,
    source_id,
    CURRENT_TIMESTAMP() AS transformed_at
FROM all_names;
