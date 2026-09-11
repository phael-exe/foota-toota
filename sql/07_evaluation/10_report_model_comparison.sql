-- Scoreboard: three-class tree vs goal model on the same TEST. Accuracy, draws, log loss and ranked probability score
-- (RPS treats home/draw/away as ordered, so predicting 'home' for an 'away' costs more than predicting 'draw').
WITH s AS (
    SELECT *,
           CAST(label_outcome = 'home' AS INT64) AS o_home, CAST(label_outcome = 'draw' AS INT64) AS o_draw, CAST(label_outcome = 'away' AS INT64) AS o_away
    FROM `PROJECT.gold.test_predictions`
)
SELECT model, matches, ROUND(correct / matches, 4) AS accuracy, draws_predicted, draws_correct,
       ROUND(SAFE_DIVIDE(draws_correct, draws_predicted), 3) AS draw_precision, ROUND(log_loss, 4) AS log_loss, ROUND(rps, 4) AS rps
FROM (
    SELECT 'v2 three-class tree' AS model, COUNT(*) AS matches, COUNTIF(prediction = label_outcome) AS correct,
           COUNTIF(prediction = 'draw') AS draws_predicted, COUNTIF(prediction = 'draw' AND label_outcome = 'draw') AS draws_correct,
           -AVG(LN(GREATEST(CASE label_outcome WHEN 'home' THEN p_home WHEN 'draw' THEN p_draw ELSE p_away END, 1e-9))) AS log_loss,
           AVG((POW(p_home - o_home, 2) + POW(p_home + p_draw - o_home - o_draw, 2)) / 2) AS rps
    FROM s
    UNION ALL
    SELECT 'goal model (2 x Poisson)', COUNT(*), COUNTIF(goal_prediction = label_outcome),
           COUNTIF(goal_prediction = 'draw'), COUNTIF(goal_prediction = 'draw' AND label_outcome = 'draw'),
           -AVG(LN(GREATEST(CASE label_outcome WHEN 'home' THEN p_home_goals WHEN 'draw' THEN p_draw_goals ELSE p_away_goals END, 1e-9))),
           AVG((POW(p_home_goals - o_home, 2) + POW(p_home_goals + p_draw_goals - o_home - o_draw, 2)) / 2)
    FROM s
)
ORDER BY accuracy DESC;

-- Is the goal model calibrated on draws? Actual draw rate by band of p_draw_goals.
SELECT CASE WHEN p_draw_goals < 0.22 THEN '1. < 0.22' WHEN p_draw_goals < 0.25 THEN '2. 0.22-0.25' WHEN p_draw_goals < 0.28 THEN '3. 0.25-0.28' ELSE '4. >= 0.28' END AS p_draw_band,
       COUNT(*) AS matches, ROUND(AVG(p_draw_goals), 3) AS p_draw_mean, ROUND(100 * COUNTIF(label_outcome = 'draw') / COUNT(*), 1) AS pct_draw_actual
FROM `PROJECT.gold.test_predictions`
GROUP BY p_draw_band ORDER BY p_draw_band;

-- How good are the expected goals themselves? Mean absolute error per side, and the exact-score hit rate.
SELECT ROUND(AVG(ABS(expected_home_goals - actual_home_goals)), 3) AS mae_home_goals,
       ROUND(AVG(ABS(expected_away_goals - actual_away_goals)), 3) AS mae_away_goals,
       ROUND(AVG(expected_home_goals), 2) AS mean_expected_home, ROUND(AVG(actual_home_goals), 2) AS mean_actual_home,
       ROUND(AVG(expected_away_goals), 2) AS mean_expected_away, ROUND(AVG(actual_away_goals), 2) AS mean_actual_away,
       COUNTIF(most_likely_score = CONCAT(actual_home_goals, 'x', actual_away_goals)) AS exact_score_hits,
       COUNT(*) AS matches
FROM `PROJECT.gold.test_predictions`;

-- Where the two disagree
SELECT prediction AS v2_prediction, goal_prediction, COUNT(*) AS matches,
       COUNTIF(label_outcome = prediction) AS v2_right, COUNTIF(label_outcome = goal_prediction) AS goal_model_right
FROM `PROJECT.gold.test_predictions`
WHERE prediction <> goal_prediction
GROUP BY 1, 2 ORDER BY matches DESC;
