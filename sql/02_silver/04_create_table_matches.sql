-- Matches conformed fact table across all leagues and sources.
-- Unifies BBD EPL matches (4,939 matches), Football-Data.co.uk (10 leagues x 3 seasons),
-- Brasileirao Historico (8,785 matches) and Football-Data.org API (10 Tier 1 competitions).
-- Partitioned by DATE(kickoff_utc), clustered by league_id, home_team_id.

CREATE OR REPLACE TABLE `PROJECT.silver.matches`
PARTITION BY DATE(kickoff_utc)
CLUSTER BY league_id, home_team_id, away_team_id AS

WITH bbd_matches AS (
    SELECT DISTINCT
        `PROJECT.silver.blank_to_null`(id) AS match_id,
        LOWER(`PROJECT.silver.blank_to_null`(league)) AS league_id,
        `PROJECT.silver.blank_to_null`(home_id) AS home_team_id,
        `PROJECT.silver.blank_to_null`(away_id) AS away_team_id,
        `PROJECT.silver.blank_to_null`(home_name) AS home_team_name,
        `PROJECT.silver.blank_to_null`(away_name) AS away_team_name,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(kickoff_utc) AS TIMESTAMP) AS kickoff_utc,
        IF(EXTRACT(MONTH FROM SAFE_CAST(`PROJECT.silver.blank_to_null`(kickoff_utc) AS TIMESTAMP)) >= 8,
           EXTRACT(YEAR FROM SAFE_CAST(`PROJECT.silver.blank_to_null`(kickoff_utc) AS TIMESTAMP)),
           EXTRACT(YEAR FROM SAFE_CAST(`PROJECT.silver.blank_to_null`(kickoff_utc) AS TIMESTAMP)) - 1) AS season,
        LOWER(`PROJECT.silver.blank_to_null`(status)) AS status,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(score_home) AS INT64) AS score_home,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(score_away) AS INT64) AS score_away,
        CASE
            WHEN LOWER(`PROJECT.silver.blank_to_null`(status)) = 'finished' AND SAFE_CAST(score_home AS INT64) > SAFE_CAST(score_away AS INT64) THEN 'home'
            WHEN LOWER(`PROJECT.silver.blank_to_null`(status)) = 'finished' AND SAFE_CAST(score_home AS INT64) = SAFE_CAST(score_away AS INT64) THEN 'draw'
            WHEN LOWER(`PROJECT.silver.blank_to_null`(status)) = 'finished' AND SAFE_CAST(score_home AS INT64) < SAFE_CAST(score_away AS INT64) THEN 'away'
        END AS outcome,
        `PROJECT.silver.blank_to_null`(linescore_home) AS linescore_home,
        `PROJECT.silver.blank_to_null`(linescore_away) AS linescore_away,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(attendance) AS INT64) AS attendance,
        `PROJECT.silver.blank_to_null`(round) AS round,
        SAFE_CAST(`PROJECT.silver.blank_to_null`(has_odds) AS BOOL) AS has_odds,
        `PROJECT.silver.blank_to_null`(kickoff_utc) AS kickoff_raw,
        `PROJECT.silver.blank_to_null`(score_home) AS score_home_raw,
        `PROJECT.silver.blank_to_null`(score_away) AS score_away_raw,
        'bigballs' AS source_id,
        batch_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.stored_matches`
),

fduk_matches AS (
    SELECT
        CONCAT('fduk_', Div, '_', REGEXP_REPLACE(COALESCE(Date, ''), '[^0-9]', ''), '_',
               REGEXP_REPLACE(COALESCE(HomeTeam, ''), '[^a-zA-Z0-9]', ''), '_',
               REGEXP_REPLACE(COALESCE(AwayTeam, ''), '[^a-zA-Z0-9]', '')) AS match_id,
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
        HomeTeam AS home_team_id,
        AwayTeam AS away_team_id,
        HomeTeam AS home_team_name,
        AwayTeam AS away_team_name,
        COALESCE(
            SAFE.PARSE_TIMESTAMP('%d/%m/%Y %H:%M', CONCAT(Date, ' ', COALESCE(Time, '15:00'))),
            SAFE.PARSE_TIMESTAMP('%d/%m/%y %H:%M', CONCAT(Date, ' ', COALESCE(Time, '15:00')))
        ) AS kickoff_utc,
        CASE
            WHEN SAFE_CAST(SUBSTR(Date, 7, 4) AS INT64) IS NOT NULL THEN
                IF(SAFE_CAST(SUBSTR(Date, 4, 2) AS INT64) >= 8,
                   SAFE_CAST(SUBSTR(Date, 7, 4) AS INT64),
                   SAFE_CAST(SUBSTR(Date, 7, 4) AS INT64) - 1)
            WHEN SAFE_CAST(SUBSTR(Date, 7, 2) AS INT64) IS NOT NULL THEN
                2000 + SAFE_CAST(SUBSTR(Date, 7, 2) AS INT64) - IF(SAFE_CAST(SUBSTR(Date, 4, 2) AS INT64) >= 8, 0, 1)
            ELSE 2024
        END AS season,
        'finished' AS status,
        SAFE_CAST(FTHG AS INT64) AS score_home,
        SAFE_CAST(FTAG AS INT64) AS score_away,
        CASE FTR
            WHEN 'H' THEN 'home'
            WHEN 'D' THEN 'draw'
            WHEN 'A' THEN 'away'
        END AS outcome,
        CONCAT(COALESCE(HTHG, ''), '-', COALESCE(HTAG, '')) AS linescore_home,
        CONCAT(COALESCE(HTAG, ''), '-', COALESCE(HTHG, '')) AS linescore_away,
        CAST(NULL AS INT64) AS attendance,
        CAST(NULL AS STRING) AS round,
        IF(B365H IS NOT NULL, TRUE, FALSE) AS has_odds,
        Date AS kickoff_raw,
        FTHG AS score_home_raw,
        FTAG AS score_away_raw,
        'football_data_uk' AS source_id,
        batch_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.football_data_uk`
    WHERE HomeTeam IS NOT NULL AND AwayTeam IS NOT NULL
      -- Drop EPL overlap if already covered by BBD
      AND Div != 'E0'
),

bra_matches AS (
    SELECT
        CONCAT('bra_', ID) AS match_id,
        'brasileirao_serie_a' AS league_id,
        mandante AS home_team_id,
        visitante AS away_team_id,
        mandante AS home_team_name,
        visitante AS away_team_name,
        COALESCE(
            SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M', CONCAT(data, ' ', COALESCE(hora, '16:00'))),
            SAFE.PARSE_TIMESTAMP('%d/%m/%Y %H:%M', CONCAT(data, ' ', COALESCE(hora, '16:00')))
        ) AS kickoff_utc,
        SAFE_CAST(SUBSTR(data, 1, 4) AS INT64) AS season,
        'finished' AS status,
        SAFE_CAST(mandante_Placar AS INT64) AS score_home,
        SAFE_CAST(visitante_Placar AS INT64) AS score_away,
        CASE
            WHEN SAFE_CAST(mandante_Placar AS INT64) > SAFE_CAST(visitante_Placar AS INT64) THEN 'home'
            WHEN SAFE_CAST(mandante_Placar AS INT64) = SAFE_CAST(visitante_Placar AS INT64) THEN 'draw'
            WHEN SAFE_CAST(mandante_Placar AS INT64) < SAFE_CAST(visitante_Placar AS INT64) THEN 'away'
        END AS outcome,
        CAST(NULL AS STRING) AS linescore_home,
        CAST(NULL AS STRING) AS linescore_away,
        CAST(NULL AS INT64) AS attendance,
        CAST(rodata AS STRING) AS round,
        FALSE AS has_odds,
        data AS kickoff_raw,
        mandante_Placar AS score_home_raw,
        visitante_Placar AS score_away_raw,
        'brasileirao_historico' AS source_id,
        batch_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.brasileirao_historico`
    WHERE mandante IS NOT NULL AND visitante IS NOT NULL
),

fdorg_matches AS (
    SELECT
        CONCAT('fdorg_', id) AS match_id,
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
        CAST(JSON_VALUE(homeTeam, '$.id') AS STRING) AS home_team_id,
        CAST(JSON_VALUE(awayTeam, '$.id') AS STRING) AS away_team_id,
        JSON_VALUE(homeTeam, '$.name') AS home_team_name,
        JSON_VALUE(awayTeam, '$.name') AS away_team_name,
        SAFE_CAST(utcDate AS TIMESTAMP) AS kickoff_utc,
        EXTRACT(YEAR FROM SAFE_CAST(utcDate AS TIMESTAMP)) AS season,
        CASE LOWER(status)
            WHEN 'timed' THEN 'scheduled'
            ELSE LOWER(status)
        END AS status,
        IF(LOWER(status) = 'finished', SAFE_CAST(JSON_VALUE(score, '$.fullTime.home') AS INT64), NULL) AS score_home,
        IF(LOWER(status) = 'finished', SAFE_CAST(JSON_VALUE(score, '$.fullTime.away') AS INT64), NULL) AS score_away,
        CASE
            WHEN LOWER(status) = 'finished' AND JSON_VALUE(score, '$.winner') = 'HOME_TEAM' THEN 'home'
            WHEN LOWER(status) = 'finished' AND JSON_VALUE(score, '$.winner') = 'DRAW'      THEN 'draw'
            WHEN LOWER(status) = 'finished' AND JSON_VALUE(score, '$.winner') = 'AWAY_TEAM' THEN 'away'
        END AS outcome,
        IF(LOWER(status) = 'finished', CONCAT(COALESCE(JSON_VALUE(score, '$.halfTime.home'), ''), '-', COALESCE(JSON_VALUE(score, '$.halfTime.away'), '')), NULL) AS linescore_home,
        IF(LOWER(status) = 'finished', CONCAT(COALESCE(JSON_VALUE(score, '$.halfTime.away'), ''), '-', COALESCE(JSON_VALUE(score, '$.halfTime.home'), '')), NULL) AS linescore_away,
        CAST(NULL AS INT64) AS attendance,
        CAST(matchday AS STRING) AS round,
        FALSE AS has_odds,
        utcDate AS kickoff_raw,
        JSON_VALUE(score, '$.fullTime.home') AS score_home_raw,
        JSON_VALUE(score, '$.fullTime.away') AS score_away_raw,
        'football_data_org' AS source_id,
        batch_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.football_data_org_matches`
    WHERE homeTeam IS NOT NULL AND awayTeam IS NOT NULL
      -- Include future scheduled games or cups (CL) not covered by static CSVs
      AND (LOWER(status) != 'finished' OR _competition_code = 'CL')
),

all_matches AS (
    SELECT * FROM bbd_matches
    UNION ALL
    SELECT * FROM fduk_matches
    UNION ALL
    SELECT * FROM bra_matches
    UNION ALL
    SELECT * FROM fdorg_matches
),

deduped AS (
    SELECT *,
        ROW_NUMBER() OVER(
            PARTITION BY match_id
            ORDER BY ingested_at DESC
        ) AS rn
    FROM all_matches
)
SELECT
    match_id,
    league_id,
    home_team_id,
    away_team_id,
    home_team_name,
    away_team_name,
    kickoff_utc,
    season,
    status,
    score_home,
    score_away,
    outcome,
    linescore_home,
    linescore_away,
    attendance,
    round,
    has_odds,
    kickoff_raw,
    score_home_raw,
    score_away_raw,
    source_id,
    batch_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM deduped
WHERE rn = 1;
