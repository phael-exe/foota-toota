WITH tree AS (
    SELECT p.match_id,
           p.predicted_label_outcome AS predicted_label,
           ROUND((SELECT prob FROM UNNEST(p.predicted_label_outcome_probs) WHERE label = 'home'), 3) AS p_home,
           ROUND((SELECT prob FROM UNNEST(p.predicted_label_outcome_probs) WHERE label = 'draw'), 3) AS p_draw,
           ROUND((SELECT prob FROM UNNEST(p.predicted_label_outcome_probs) WHERE label = 'away'), 3) AS p_away
    FROM ML.PREDICT(MODEL `pdm-andre-2026.gold.outcome_model_v2`,
        (SELECT * FROM `pdm-andre-2026.gold.match_features` WHERE split_set = 'PREDICT')) p
)
SELECT FORMAT_TIMESTAMP('%d/%m %H:%M', m.kickoff_utc) AS kickoff,
       th.team_name AS home_team, ta.team_name AS away_team,
       t.predicted_label, t.p_home, t.p_draw, t.p_away,
       g.goal_prediction, g.expected_home_goals, g.expected_away_goals, g.most_likely_score,
       g.p_home_goals, g.p_draw_goals, g.p_away_goals
FROM tree t
JOIN `pdm-andre-2026.silver.matches` m USING (match_id)
JOIN `pdm-andre-2026.silver.teams` th ON th.team_id = m.home_team_id
JOIN `pdm-andre-2026.silver.teams` ta ON ta.team_id = m.away_team_id
JOIN `pdm-andre-2026.gold.predictions_goals` g USING (match_id)
ORDER BY m.kickoff_utc
LIMIT 10;
