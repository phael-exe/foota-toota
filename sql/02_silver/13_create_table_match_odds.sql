-- Match betting odds fact table (1X2 market & Over/Under 2.5 goals).
-- Pre-game closing odds from Bet365 and market consensus.

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
  AND B365H IS NOT NULL;
