-- G8 (BLOCKING): in the training tables, every labelled match has both goal labels and they
-- agree with label_outcome (more home goals = 'home', equal = 'draw', fewer = 'away').
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT label_outcome, label_goals_home, label_goals_away
        FROM `PROJECT.gold.match_training_brasileirao`
        UNION ALL
        SELECT label_outcome, label_goals_home, label_goals_away
        FROM `PROJECT.gold.match_training_epl`
    )
    WHERE label_outcome IS NOT NULL
      AND (label_goals_home IS NULL OR label_goals_away IS NULL
           OR label_outcome != CASE
                  WHEN label_goals_home > label_goals_away THEN 'home'
                  WHEN label_goals_home = label_goals_away THEN 'draw'
                  ELSE 'away'
              END)
) AS 'G8: goal labels missing or inconsistent with label_outcome';
