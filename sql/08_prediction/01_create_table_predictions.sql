-- The 350 scheduled matches with all three probabilities. Model: v2 (boosted trees).
-- Their features were built from finished matches only, which is exactly the production
-- scenario: nothing about the match itself is available yet.
CREATE OR REPLACE TABLE `PROJECT.gold.predictions` AS
SELECT
    m.match_id,
    m.kickoff_utc,
    t_home.team_name AS home_team,
    t_away.team_name AS away_team,
    p.predicted_label_outcome AS prediction,
    ROUND((SELECT prob FROM UNNEST(p.predicted_label_outcome_probs) WHERE label = 'home'), 3) AS p_home,
    ROUND((SELECT prob FROM UNNEST(p.predicted_label_outcome_probs) WHERE label = 'draw'), 3) AS p_draw,
    ROUND((SELECT prob FROM UNNEST(p.predicted_label_outcome_probs) WHERE label = 'away'), 3) AS p_away,
    ROUND(p.home_avg_points_last_5, 2) AS home_form_last_5,
    ROUND(p.away_avg_points_last_5, 2) AS away_form_last_5,
    CURRENT_TIMESTAMP() AS predicted_at
FROM ML.PREDICT(
    MODEL `PROJECT.gold.outcome_model_v2`,
    (SELECT * FROM `PROJECT.gold.match_features` WHERE split_set = 'PREDICT')
) p
JOIN `PROJECT.silver.matches` m USING (match_id)
JOIN `PROJECT.silver.teams` t_home ON t_home.team_id = m.home_team_id
JOIN `PROJECT.silver.teams` t_away ON t_away.team_id = m.away_team_id;
