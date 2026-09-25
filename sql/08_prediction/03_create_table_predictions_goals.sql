-- Next fixtures with both models side by side: the three-class tree (prediction, p_*) and the goal model
-- (goal_prediction, expected goals, p_*_goals, most likely score).
CREATE OR REPLACE TABLE `PROJECT.gold.predictions_goals` AS
WITH base AS (
    SELECT * FROM `PROJECT.gold.match_features` WHERE split_set = 'PREDICT'
), lambdas AS (
    SELECT h.match_id, GREATEST(h.predicted_home_goals, 0.05) AS lambda_home, GREATEST(a.predicted_away_goals, 0.05) AS lambda_away
    FROM ML.PREDICT(MODEL `PROJECT.gold.goals_home_model`, (SELECT * FROM base)) h
    JOIN ML.PREDICT(MODEL `PROJECT.gold.goals_away_model`, (SELECT * FROM base)) a USING (match_id)
), fact AS (
    SELECT [1.0, 1.0, 2.0, 6.0, 24.0, 120.0, 720.0, 5040.0, 40320.0, 362880.0, 3628800.0] AS f
), score_grid AS (
    SELECT l.match_id, i, j,
           EXP(-l.lambda_home) * POW(l.lambda_home, i) / (SELECT f[OFFSET(i)] FROM fact)
         * EXP(-l.lambda_away) * POW(l.lambda_away, j) / (SELECT f[OFFSET(j)] FROM fact) AS p
    FROM lambdas l, UNNEST(GENERATE_ARRAY(0, 10)) AS i, UNNEST(GENERATE_ARRAY(0, 10)) AS j
), agg AS (
    SELECT match_id,
           SUM(IF(i > j, p, 0)) AS p_home_goals, SUM(IF(i = j, p, 0)) AS p_draw_goals, SUM(IF(i < j, p, 0)) AS p_away_goals,
           ARRAY_AGG(STRUCT(i, j) ORDER BY p DESC LIMIT 1)[OFFSET(0)] AS top
    FROM score_grid GROUP BY match_id
)
SELECT p.match_id, p.kickoff_utc, p.home_team, p.away_team,
       p.prediction, p.p_home, p.p_draw, p.p_away,
       ROUND(l.lambda_home, 2) AS expected_home_goals, ROUND(l.lambda_away, 2) AS expected_away_goals,
       ROUND(a.p_home_goals, 3) AS p_home_goals, ROUND(a.p_draw_goals, 3) AS p_draw_goals, ROUND(a.p_away_goals, 3) AS p_away_goals,
       CASE WHEN a.p_home_goals >= a.p_draw_goals AND a.p_home_goals >= a.p_away_goals THEN 'home'
            WHEN a.p_away_goals >= a.p_draw_goals THEN 'away' ELSE 'draw' END AS goal_prediction,
       CONCAT(a.top.i, 'x', a.top.j) AS most_likely_score,
       CURRENT_TIMESTAMP() AS predicted_at
FROM `PROJECT.gold.predictions` p
JOIN lambdas l USING (match_id)
JOIN agg a USING (match_id);

SELECT FORMAT_TIMESTAMP('%d/%m %H:%M', kickoff_utc) AS kickoff, home_team, away_team,
       prediction, goal_prediction, most_likely_score, expected_home_goals, expected_away_goals, p_draw, p_draw_goals
FROM `PROJECT.gold.predictions_goals` ORDER BY kickoff_utc LIMIT 10;
