-- Teams / Clubs dimension.
-- Integrates BBD EPL clubs, Transfermarkt global directory (796 clubs),
-- and all clubs present in multi-league match datasets (Football-Data UK, Brasileirao, Football-Data.org).

CREATE OR REPLACE TABLE `PROJECT.silver.teams` AS
WITH bbd_teams AS (
    SELECT
        `PROJECT.silver.blank_to_null`(id) AS team_id,
        `PROJECT.silver.blank_to_null`(name) AS team_name,
        LOWER(`PROJECT.silver.blank_to_null`(league)) AS league_id,
        'football' AS sport,
        COALESCE(
            `PROJECT.silver.blank_to_null`(short_name),
            `PROJECT.silver.blank_to_null`(code)
        ) AS short_name,
        `PROJECT.silver.blank_to_null`(logo_url) AS logo_url,
        CAST(NULL AS STRING) AS stadium_name,
        CAST(NULL AS FLOAT64) AS market_value_eur,
        CAST(NULL AS INT64) AS squad_size,
        'bigballs' AS source_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.teams`
),
tm_clubs AS (
    SELECT
        CAST(`PROJECT.silver.blank_to_null`(club_id) AS STRING) AS team_id,
        `PROJECT.silver.blank_to_null`(name) AS team_name,
        LOWER(`PROJECT.silver.blank_to_null`(domestic_competition_id)) AS league_id,
        'football' AS sport,
        `PROJECT.silver.blank_to_null`(club_code) AS short_name,
        CAST(NULL AS STRING) AS logo_url,
        `PROJECT.silver.blank_to_null`(stadium_name) AS stadium_name,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(total_market_value) AS FLOAT64) AS market_value_eur,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(squad_size) AS INT64) AS squad_size,
        'transfermarkt' AS source_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.transfermarkt_clubs`
    WHERE `PROJECT.silver.blank_to_null`(club_id) IS NOT NULL
),
fduk_teams AS (
    SELECT DISTINCT
        team_name AS team_id,
        team_name,
        CASE Div
            WHEN 'E0'  THEN 'epl'
            WHEN 'E1'  THEN 'championship'
            WHEN 'SP1' THEN 'la_liga'
            WHEN 'I1'  THEN 'serie_a'
            WHEN 'D1'  THEN 'bundesliga'
            WHEN 'F1'  THEN 'ligue_1'
            WHEN 'N1'  THEN 'eredivisie'
            WHEN 'P1'  THEN 'primeira_liga'
            WHEN 'B1'  THEN 'belgian_pro_league'
            WHEN 'SC0' THEN 'scottish_premiership'
            ELSE LOWER(Div)
        END AS league_id,
        'football' AS sport,
        team_name AS short_name,
        CAST(NULL AS STRING) AS logo_url,
        CAST(NULL AS STRING) AS stadium_name,
        CAST(NULL AS FLOAT64) AS market_value_eur,
        CAST(NULL AS INT64) AS squad_size,
        'football_data_uk' AS source_id,
        source_file,
        ingested_at
    FROM (
        SELECT HomeTeam AS team_name, Div, source_file, ingested_at FROM `PROJECT.bronze.football_data_uk`
        UNION ALL
        SELECT AwayTeam AS team_name, Div, source_file, ingested_at FROM `PROJECT.bronze.football_data_uk`
    )
    WHERE team_name IS NOT NULL
),
bra_teams AS (
    SELECT DISTINCT
        team_name AS team_id,
        team_name,
        'brasileirao_serie_a' AS league_id,
        'football' AS sport,
        team_name AS short_name,
        CAST(NULL AS STRING) AS logo_url,
        CAST(NULL AS STRING) AS stadium_name,
        CAST(NULL AS FLOAT64) AS market_value_eur,
        CAST(NULL AS INT64) AS squad_size,
        'brasileirao_historico' AS source_id,
        source_file,
        ingested_at
    FROM (
        SELECT mandante AS team_name, source_file, ingested_at FROM `PROJECT.bronze.brasileirao_historico`
        UNION ALL
        SELECT visitante AS team_name, source_file, ingested_at FROM `PROJECT.bronze.brasileirao_historico`
    )
    WHERE team_name IS NOT NULL
),
fdorg_teams AS (
    SELECT DISTINCT
        team_id,
        team_name,
        CASE _competition_code
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
            ELSE LOWER(_competition_code)
        END AS league_id,
        'football' AS sport,
        team_name AS short_name,
        CAST(NULL AS STRING) AS logo_url,
        CAST(NULL AS STRING) AS stadium_name,
        CAST(NULL AS FLOAT64) AS market_value_eur,
        CAST(NULL AS INT64) AS squad_size,
        'football_data_org' AS source_id,
        source_file,
        ingested_at
    FROM (
        SELECT
            CAST(JSON_VALUE(homeTeam, '$.id') AS STRING) AS team_id,
            JSON_VALUE(homeTeam, '$.name') AS team_name,
            _competition_code,
            source_file,
            ingested_at
        FROM `PROJECT.bronze.football_data_org_matches`
        UNION ALL
        SELECT
            CAST(JSON_VALUE(awayTeam, '$.id') AS STRING) AS team_id,
            JSON_VALUE(awayTeam, '$.name') AS team_name,
            _competition_code,
            source_file,
            ingested_at
        FROM `PROJECT.bronze.football_data_org_matches`
    )
    WHERE team_id IS NOT NULL AND team_name IS NOT NULL
),
all_teams AS (
    SELECT * FROM bbd_teams
    UNION ALL SELECT * FROM tm_clubs
    UNION ALL SELECT * FROM fduk_teams
    UNION ALL SELECT * FROM bra_teams
    UNION ALL SELECT * FROM fdorg_teams
),
deduped AS (
    SELECT *,
        ROW_NUMBER() OVER(
            PARTITION BY team_id
            ORDER BY CASE source_id
                WHEN 'bigballs'              THEN 1
                WHEN 'transfermarkt'         THEN 2
                WHEN 'football_data_uk'      THEN 3
                WHEN 'brasileirao_historico' THEN 4
                ELSE 5
            END
        ) AS rn
    FROM all_teams
)
SELECT
    team_id,
    team_name,
    league_id,
    sport,
    short_name,
    logo_url,
    stadium_name,
    market_value_eur,
    squad_size,
    source_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM deduped
WHERE rn = 1;
