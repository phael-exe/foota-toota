-- Match betting odds fact table (1X2 market & Over/Under 2.5 goals).
-- Pre-game closing odds from Bet365 and market consensus. Built after silver.matches: the
-- Brasileirao odds attach to whichever source holds the game there.

CREATE OR REPLACE TABLE `PROJECT.silver.match_odds` AS
-- Football-Data.co.uk, 10 European leagues: a game silver.matches keeps under another source's id
-- (the EPL under Big Balls) takes that id, as in silver.match_stats
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
        f.B365H, f.B365D, f.B365A
    FROM `PROJECT.bronze.football_data_uk` f
    LEFT JOIN `PROJECT.silver.team_map` th
           ON th.source_id = 'football_data_uk' AND th.raw_team_id = f.HomeTeam
    LEFT JOIN `PROJECT.silver.team_map` ta
           ON ta.source_id = 'football_data_uk' AND ta.raw_team_id = f.AwayTeam
    WHERE f.HomeTeam IS NOT NULL AND f.AwayTeam IS NOT NULL
      AND f.B365H IS NOT NULL
)
SELECT
    COALESCE(own.match_id, other.match_id) AS match_id,
    -- Bet365 1X2
    SAFE_CAST(o.B365H AS FLOAT64) AS bet365_home_win,
    SAFE_CAST(o.B365D AS FLOAT64) AS bet365_draw,
    SAFE_CAST(o.B365A AS FLOAT64) AS bet365_away_win,
    -- Placeholders for extended bookmakers
    CAST(NULL AS FLOAT64) AS pinnacle_home_win,
    CAST(NULL AS FLOAT64) AS pinnacle_draw,
    CAST(NULL AS FLOAT64) AS pinnacle_away_win,
    CAST(NULL AS FLOAT64) AS market_avg_home_win,
    CAST(NULL AS FLOAT64) AS market_avg_draw,
    CAST(NULL AS FLOAT64) AS market_avg_away_win,
    CAST(NULL AS FLOAT64) AS bet365_over_2_5,
    CAST(NULL AS FLOAT64) AS bet365_under_2_5,
    CAST(NULL AS FLOAT64) AS market_avg_over_2_5,
    CAST(NULL AS FLOAT64) AS market_avg_under_2_5,
    CURRENT_TIMESTAMP() AS transformed_at
FROM fduk o
LEFT JOIN `PROJECT.silver.matches` own
       ON own.match_id = o.fduk_match_id
LEFT JOIN `PROJECT.silver.matches` other
       ON own.match_id IS NULL
      AND other.league_id = o.league_id
      AND other.season = o.season
      AND other.home_team_id = o.home_team_id
      AND other.away_team_id = o.away_team_id
WHERE COALESCE(own.match_id, other.match_id) IS NOT NULL

UNION ALL

-- Brasileirao closing odds (Football-Data.co.uk Brazil file, 2012 on), matched by
-- (season, home, away) because a season is a double round robin
SELECT
    m.match_id,
    b.B365CH AS bet365_home_win,
    b.B365CD AS bet365_draw,
    b.B365CA AS bet365_away_win,
    b.PSCH AS pinnacle_home_win,
    b.PSCD AS pinnacle_draw,
    b.PSCA AS pinnacle_away_win,
    b.AvgCH AS market_avg_home_win,
    b.AvgCD AS market_avg_draw,
    b.AvgCA AS market_avg_away_win,
    CAST(NULL AS FLOAT64) AS bet365_over_2_5,
    CAST(NULL AS FLOAT64) AS bet365_under_2_5,
    CAST(NULL AS FLOAT64) AS market_avg_over_2_5,
    CAST(NULL AS FLOAT64) AS market_avg_under_2_5,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.football_data_uk_bra` b
LEFT JOIN `PROJECT.silver.team_alias` ah
       ON ah.league_id = 'brasileirao_serie_a' AND ah.source_id = 'football_data_uk'
      AND ah.raw_name = b.Home
LEFT JOIN `PROJECT.silver.team_alias` aa
       ON aa.league_id = 'brasileirao_serie_a' AND aa.source_id = 'football_data_uk'
      AND aa.raw_name = b.Away
JOIN `PROJECT.silver.matches` m
  ON  m.league_id = 'brasileirao_serie_a'
  AND m.season = b.Season
  AND m.home_team_id = COALESCE(ah.team_id, b.Home)
  AND m.away_team_id = COALESCE(aa.team_id, b.Away)
WHERE COALESCE(b.PSCH, b.B365CH, b.AvgCH) IS NOT NULL;
