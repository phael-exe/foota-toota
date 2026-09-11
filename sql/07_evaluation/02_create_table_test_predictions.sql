-- Every model scored on the held-out set, one row per test match: the three-class tree (prediction, p_*) and the
-- goal model (goal_prediction, expected goals, p_*_goals, most likely score), next to the actual result. Materialised
-- because it calls ML.PREDICT three times and because it is the record of what was evaluated.
-- Expected goals (lambda) per side -> independent Poisson score distribution (0..10 goals) ->
-- p_home_goals = P(i > j), p_draw_goals = P(i = j), p_away_goals = P(i < j); goal_prediction = argmax.
CREATE OR REPLACE TABLE `PROJECT.gold.test_predictions` AS
WITH lambdas AS (
    SELECT h.match_id, h.label_outcome,
           GREATEST(h.predicted_home_goals, 0.05) AS lambda_home,
           GREATEST(a.predicted_away_goals, 0.05) AS lambda_away
    FROM ML.PREDICT(MODEL `PROJECT.gold.goals_home_model`, (SELECT * FROM `PROJECT.gold.test_set`)) h
    JOIN ML.PREDICT(MODEL `PROJECT.gold.goals_away_model`, (SELECT * FROM `PROJECT.gold.test_set`)) a USING (match_id)
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
), v2 AS (
    SELECT match_id, predicted_label_outcome AS prediction,
           (SELECT prob FROM UNNEST(predicted_label_outcome_probs) WHERE label = 'home') AS p_home,
           (SELECT prob FROM UNNEST(predicted_label_outcome_probs) WHERE label = 'draw') AS p_draw,
           (SELECT prob FROM UNNEST(predicted_label_outcome_probs) WHERE label = 'away') AS p_away
    FROM ML.PREDICT(MODEL `PROJECT.gold.outcome_model_v2`, (SELECT * FROM `PROJECT.gold.test_set`))
)
SELECT
    l.match_id, l.label_outcome, m.score_home AS actual_home_goals, m.score_away AS actual_away_goals,
    -- three-class tree
    v2.prediction, ROUND(v2.p_home, 3) AS p_home, ROUND(v2.p_draw, 3) AS p_draw, ROUND(v2.p_away, 3) AS p_away,
    -- goal model
    ROUND(l.lambda_home, 2) AS expected_home_goals, ROUND(l.lambda_away, 2) AS expected_away_goals,
    ROUND(a.p_home_goals, 3) AS p_home_goals, ROUND(a.p_draw_goals, 3) AS p_draw_goals, ROUND(a.p_away_goals, 3) AS p_away_goals,
    CASE WHEN a.p_home_goals >= a.p_draw_goals AND a.p_home_goals >= a.p_away_goals THEN 'home'
         WHEN a.p_away_goals >= a.p_draw_goals THEN 'away' ELSE 'draw' END AS goal_prediction,
    CONCAT(a.top.i, 'x', a.top.j) AS most_likely_score
FROM lambdas l
JOIN agg a USING (match_id)
JOIN v2 USING (match_id)
JOIN `PROJECT.silver.matches` m USING (match_id);
