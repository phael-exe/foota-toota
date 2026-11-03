-- Match stats fact table (shots, fouls, corners, cards).
-- Sourced from Football-Data.co.uk across 10 European leagues. A game silver.matches keeps under
-- another source's id (the EPL under Big Balls) takes that id: same league, season and clubs.
-- Games silver.matches does not hold are left out, so every row meets its match.

CREATE OR REPLACE TABLE `PROJECT.silver.match_stats` AS
WITH fduk AS (
    SELECT
        CONCAT('fduk_', f.Div, '_', REGEXP_REPLACE(COALESCE(f.Date, ''), '[^0-9]', ''), '_',
               REGEXP_REPLACE(COALESCE(f.HomeTeam, ''), '[^a-zA-Z0-9]', ''), '_',
               REGEXP_REPLACE(COALESCE(f.AwayTeam, ''), '[^a-zA-Z0-9]', '')) AS fduk_match_id,
        CASE f.Div
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
            ELSE LOWER(f.Div)
        END AS league_id,
        SAFE_CAST(REGEXP_EXTRACT(f.source_file, r'season=(\d{4})-') AS INT64) AS season,
        COALESCE(th.team_id, f.HomeTeam) AS home_team_id,
        COALESCE(ta.team_id, f.AwayTeam) AS away_team_id,
        f.HS, f.`AS`, f.HST, f.AST, f.HF, f.AF, f.HC, f.AC, f.HY, f.AY, f.HR, f.AR, f.Referee
    FROM `PROJECT.bronze.football_data_uk` f
    LEFT JOIN `PROJECT.silver.team_map` th
           ON th.source_id = 'football_data_uk' AND th.raw_team_id = f.HomeTeam
    LEFT JOIN `PROJECT.silver.team_map` ta
           ON ta.source_id = 'football_data_uk' AND ta.raw_team_id = f.AwayTeam
    WHERE f.HomeTeam IS NOT NULL AND f.AwayTeam IS NOT NULL
)
SELECT
    COALESCE(own.match_id, other.match_id) AS match_id,
    SAFE_CAST(s.HS AS INT64) AS home_shots,
    SAFE_CAST(s.`AS` AS INT64) AS away_shots,
    SAFE_CAST(s.HST AS INT64) AS home_shots_on_target,
    SAFE_CAST(s.AST AS INT64) AS away_shots_on_target,
    SAFE_CAST(s.HF AS INT64) AS home_fouls,
    SAFE_CAST(s.AF AS INT64) AS away_fouls,
    SAFE_CAST(s.HC AS INT64) AS home_corners,
    SAFE_CAST(s.AC AS INT64) AS away_corners,
    SAFE_CAST(s.HY AS INT64) AS home_yellow_cards,
    SAFE_CAST(s.AY AS INT64) AS away_yellow_cards,
    SAFE_CAST(s.HR AS INT64) AS home_red_cards,
    SAFE_CAST(s.AR AS INT64) AS away_red_cards,
    s.Referee AS referee,
    CURRENT_TIMESTAMP() AS transformed_at
FROM fduk s
LEFT JOIN `PROJECT.silver.matches` own
       ON own.match_id = s.fduk_match_id
LEFT JOIN `PROJECT.silver.matches` other
       ON own.match_id IS NULL
      AND other.league_id = s.league_id
      AND other.season = s.season
      AND other.home_team_id = s.home_team_id
      AND other.away_team_id = s.away_team_id
WHERE COALESCE(own.match_id, other.match_id) IS NOT NULL;
