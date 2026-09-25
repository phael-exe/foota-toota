-- Match betting odds fact table (1X2 market & Over/Under 2.5 goals).
-- Pre-game closing odds from Bet365, Pinnacle and market consensus.

CREATE OR REPLACE TABLE `PROJECT.silver.match_odds` AS
SELECT
    CONCAT('fduk_', Div, '_', REGEXP_REPLACE(COALESCE(Date, ''), '[^0-9]', ''), '_',
           REGEXP_REPLACE(COALESCE(HomeTeam, ''), '[^a-zA-Z0-9]', ''), '_',
           REGEXP_REPLACE(COALESCE(AwayTeam, ''), '[^a-zA-Z0-9]', '')) AS match_id,
    -- Bet365 1X2
    SAFE_CAST(B365H AS FLOAT64) AS bet365_home_win,
    SAFE_CAST(B365D AS FLOAT64) AS bet365_draw,
    SAFE_CAST(B365A AS FLOAT64) AS bet365_away_win,
    -- Pinnacle 1X2
    SAFE_CAST(PSH AS FLOAT64) AS pinnacle_home_win,
    SAFE_CAST(PSD AS FLOAT64) AS pinnacle_draw,
    SAFE_CAST(PSA AS FLOAT64) AS pinnacle_away_win,
    -- Market Average 1X2
    SAFE_CAST(AvgH AS FLOAT64) AS market_avg_home_win,
    SAFE_CAST(AvgD AS FLOAT64) AS market_avg_draw,
    SAFE_CAST(AvgA AS FLOAT64) AS market_avg_away_win,
    -- Over / Under 2.5 Gols
    SAFE_CAST(`B365>2.5` AS FLOAT64) AS bet365_over_2_5,
    SAFE_CAST(`B365<2.5` AS FLOAT64) AS bet365_under_2_5,
    SAFE_CAST(`Avg>2.5` AS FLOAT64) AS market_avg_over_2_5,
    SAFE_CAST(`Avg<2.5` AS FLOAT64) AS market_avg_under_2_5,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.football_data_uk`
WHERE HomeTeam IS NOT NULL AND AwayTeam IS NOT NULL
  AND (B365H IS NOT NULL OR PSH IS NOT NULL OR AvgH IS NOT NULL);
