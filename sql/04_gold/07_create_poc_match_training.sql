-- Training tables for the PoC leagues: the feature store plus the goal labels, so a goal
-- model needs no join. The goals are labels only (label_*), never features: rule G3 keeps the
-- match's own score out of gold.match_features, and G8 checks these labels against the outcome.
-- Rows still to be played (split_set = 'PREDICT') carry NULL labels.

-- 1. Brasileirao Serie A
CREATE OR REPLACE TABLE `PROJECT.gold.match_training_brasileirao` AS
SELECT
    f.*,
    IF(m.status = 'finished', m.score_home, NULL) AS label_goals_home,
    IF(m.status = 'finished', m.score_away, NULL) AS label_goals_away
FROM `PROJECT.gold.match_features_brasileirao` f
LEFT JOIN `PROJECT.silver.matches` m USING (match_id);

-- 2. English Premier League
CREATE OR REPLACE TABLE `PROJECT.gold.match_training_epl` AS
SELECT
    f.*,
    IF(m.status = 'finished', m.score_home, NULL) AS label_goals_home,
    IF(m.status = 'finished', m.score_away, NULL) AS label_goals_away
FROM `PROJECT.gold.match_features_epl` f
LEFT JOIN `PROJECT.silver.matches` m USING (match_id);
