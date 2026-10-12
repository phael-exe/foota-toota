-- Match betting odds fact table (1X2 market & Over/Under 2.5 goals).
-- Pre-game closing odds from Bet365 and market consensus. Built after silver.matches: the
-- Brasileirao odds attach to whichever source holds the game there.

CREATE OR REPLACE TABLE `PROJECT.silver.match_odds` AS
SELECT
    CONCAT('fduk_', Div, '_', REGEXP_REPLACE(COALESCE(Date, ''), '[^0-9]', ''), '_',
           REGEXP_REPLACE(COALESCE(HomeTeam, ''), '[^a-zA-Z0-9]', ''), '_',
           REGEXP_REPLACE(COALESCE(AwayTeam, ''), '[^a-zA-Z0-9]', '')) AS match_id,
    -- Bet365 1X2
    SAFE_CAST(B365H AS FLOAT64) AS bet365_home_win,
    SAFE_CAST(B365D AS FLOAT64) AS bet365_draw,
    SAFE_CAST(B365A AS FLOAT64) AS bet365_away_win,
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
FROM `PROJECT.bronze.football_data_uk`
WHERE HomeTeam IS NOT NULL AND AwayTeam IS NOT NULL
  AND B365H IS NOT NULL

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
