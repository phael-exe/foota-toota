-- Matches conformed fact table across all leagues and sources.
-- Unifies BBD EPL matches (4,939 matches), Football-Data.co.uk (10 leagues from 2022/23 to the
-- current season, plus the Brazil file for the Brasileirao from 2025), Brasileirao Historico
-- (8,785 matches, 2003-2024) and the Football-Data.org API (current season of 10 competitions).
-- Clubs carry the canonical ids of silver.team_map, so one game seen by several sources meets
-- itself below and is kept once.
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
        COALESCE(th.team_id, HomeTeam) AS home_team_id,
        COALESCE(ta.team_id, AwayTeam) AS away_team_id,
        COALESCE(th.team_name, HomeTeam) AS home_team_name,
        COALESCE(ta.team_name, AwayTeam) AS away_team_name,
        -- the files give UK local time
        COALESCE(
            SAFE.PARSE_TIMESTAMP('%d/%m/%Y %H:%M', CONCAT(Date, ' ', COALESCE(Time, '15:00')), 'Europe/London'),
            SAFE.PARSE_TIMESTAMP('%d/%m/%y %H:%M', CONCAT(Date, ' ', COALESCE(Time, '15:00')), 'Europe/London')
        ) AS kickoff_utc,
        -- the season of the file (season=2022-2023 is 2022): a July game opens the new season
        -- in Belgium and Scotland, so the month says nothing
        SAFE_CAST(REGEXP_EXTRACT(source_file, r'season=(\d{4})-') AS INT64) AS season,
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
    LEFT JOIN `PROJECT.silver.team_map` th
           ON th.source_id = 'football_data_uk' AND th.raw_team_id = HomeTeam
    LEFT JOIN `PROJECT.silver.team_map` ta
           ON ta.source_id = 'football_data_uk' AND ta.raw_team_id = AwayTeam
    WHERE HomeTeam IS NOT NULL AND AwayTeam IS NOT NULL
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
        -- data is dd/mm/yyyy; a January/February game closes the previous season (Covid 2020)
        SAFE_CAST(SUBSTR(data, 7, 4) AS INT64)
            - IF(SAFE_CAST(SUBSTR(data, 4, 2) AS INT64) <= 2, 1, 0) AS season,
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

-- Football-Data.co.uk Brazil file: fills the seasons after the historico ends (2025 on).
-- Club names go through silver.team_alias so they match the historico ids.
fduk_bra_matches AS (
    SELECT
        CONCAT('fduk_BRA_', FORMAT_DATE('%d%m%Y', b.Date), '_',
               REGEXP_REPLACE(b.Home, '[^a-zA-Z0-9]', ''), '_',
               REGEXP_REPLACE(b.Away, '[^a-zA-Z0-9]', '')) AS match_id,
        'brasileirao_serie_a' AS league_id,
        COALESCE(ah.team_id, b.Home) AS home_team_id,
        COALESCE(aa.team_id, b.Away) AS away_team_id,
        COALESCE(ah.team_id, b.Home) AS home_team_name,
        COALESCE(aa.team_id, b.Away) AS away_team_name,
        -- the file gives UK local time
        SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M',
                             CONCAT(CAST(b.Date AS STRING), ' ', COALESCE(b.Time, '20:00')),
                             'Europe/London') AS kickoff_utc,
        b.Season AS season,
        'finished' AS status,
        b.HG AS score_home,
        b.AG AS score_away,
        CASE b.Res
            WHEN 'H' THEN 'home'
            WHEN 'D' THEN 'draw'
            WHEN 'A' THEN 'away'
        END AS outcome,
        CAST(NULL AS STRING) AS linescore_home,
        CAST(NULL AS STRING) AS linescore_away,
        CAST(NULL AS INT64) AS attendance,
        CAST(NULL AS STRING) AS round,
        b.PSCH IS NOT NULL OR b.B365CH IS NOT NULL AS has_odds,
        CAST(b.Date AS STRING) AS kickoff_raw,
        CAST(b.HG AS STRING) AS score_home_raw,
        CAST(b.AG AS STRING) AS score_away_raw,
        'football_data_uk' AS source_id,
        b.batch_id,
        b.source_file,
        b.ingested_at
    FROM `PROJECT.bronze.football_data_uk_bra` b
    LEFT JOIN `PROJECT.silver.team_alias` ah
           ON ah.league_id = 'brasileirao_serie_a' AND ah.source_id = 'football_data_uk'
          AND ah.raw_name = b.Home
    LEFT JOIN `PROJECT.silver.team_alias` aa
           ON aa.league_id = 'brasileirao_serie_a' AND aa.source_id = 'football_data_uk'
          AND aa.raw_name = b.Away
    WHERE b.Home IS NOT NULL AND b.Away IS NOT NULL AND b.Date IS NOT NULL
      -- a row without a score was never played (Chapecoense x Atletico-MG, Dec 2016)
      AND b.HG IS NOT NULL AND b.AG IS NOT NULL
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
        COALESCE(th.team_id, CAST(JSON_VALUE(homeTeam, '$.id') AS STRING)) AS home_team_id,
        COALESCE(ta.team_id, CAST(JSON_VALUE(awayTeam, '$.id') AS STRING)) AS away_team_id,
        COALESCE(th.team_name, JSON_VALUE(homeTeam, '$.name')) AS home_team_name,
        COALESCE(ta.team_name, JSON_VALUE(awayTeam, '$.name')) AS away_team_name,
        SAFE_CAST(utcDate AS TIMESTAMP) AS kickoff_utc,
        -- the season starts in its first year: 2026/27 is 2026, not 2027 for games after January
        COALESCE(
            EXTRACT(YEAR FROM SAFE_CAST(JSON_VALUE(season, '$.startDate') AS DATE)),
            EXTRACT(YEAR FROM SAFE_CAST(utcDate AS TIMESTAMP))
        ) AS season,
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
    LEFT JOIN `PROJECT.silver.team_map` th
           ON th.source_id = 'football_data_org'
          AND th.raw_team_id = CAST(JSON_VALUE(homeTeam, '$.id') AS STRING)
    LEFT JOIN `PROJECT.silver.team_map` ta
           ON ta.source_id = 'football_data_org'
          AND ta.raw_team_id = CAST(JSON_VALUE(awayTeam, '$.id') AS STRING)
    WHERE homeTeam IS NOT NULL AND awayTeam IS NOT NULL
),

all_matches AS (
    SELECT * FROM bbd_matches
    UNION ALL
    SELECT * FROM fduk_matches
    UNION ALL
    SELECT * FROM bra_matches
    UNION ALL
    SELECT * FROM fduk_bra_matches
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
),

-- A game held by several sources under different match ids is one (league, season, home, away):
-- a domestic league is a double round robin. Keep its finished version first, then the source
-- ranked first for the league: the longest history for the Brasileirao, the Big Balls ids of the
-- PoC for the EPL, the stats and odds of Football-Data.co.uk elsewhere. Football-Data.org fills
-- what the files do not hold yet: fixtures, and results newer than the last file. Outside the
-- Brasileirao, rows of one source are never dropped against each other (the Scottish split and
-- the Belgian play-offs repeat a fixture within a season). The Champions League has a single
-- source and a knockout phase, so it is kept as it comes.
ranked AS (
    SELECT *,
        CASE
            WHEN league_id = 'brasileirao_serie_a' THEN
                CASE source_id WHEN 'brasileirao_historico' THEN 1 WHEN 'football_data_uk' THEN 2 ELSE 3 END
            WHEN league_id = 'epl' THEN
                CASE source_id WHEN 'bigballs' THEN 1 WHEN 'football_data_uk' THEN 2 ELSE 3 END
            ELSE
                CASE source_id WHEN 'football_data_uk' THEN 1 ELSE 2 END
        END AS source_rank
    FROM deduped
    WHERE rn = 1
),

fixtures AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY league_id, season, home_team_id, away_team_id
            ORDER BY status = 'finished' DESC, source_rank
        ) AS fixture_rn,
        MIN(IF(status = 'finished', source_rank, NULL)) OVER fixture AS best_finished_rank,
        MIN(source_rank) OVER fixture AS best_rank
    FROM ranked
    WINDOW fixture AS (PARTITION BY league_id, season, home_team_id, away_team_id)
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
FROM fixtures
WHERE CASE
    WHEN league_id = 'champions_league' THEN TRUE
    WHEN league_id = 'brasileirao_serie_a' THEN fixture_rn = 1
    ELSE source_rank = COALESCE(best_finished_rank, best_rank)
         AND (best_finished_rank IS NULL OR status = 'finished')
END;
