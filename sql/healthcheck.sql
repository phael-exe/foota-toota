-- Production health check: one query that proves the pipeline is live in the cloud right now.
-- Run it before leaving for the presentation and again on the projector: ./run.sh healthcheck.sql
-- Every row must say OK. Nothing here trains or rebuilds anything; it only reads.
WITH checks AS (
    SELECT 'bronze: 8 tables loaded' AS item,
           (SELECT COUNT(*) FROM `PROJECT.bronze.__TABLES__` WHERE table_id NOT LIKE 'ext_%') = 8 AS ok,
           CONCAT(CAST((SELECT COUNT(*) FROM `PROJECT.bronze.__TABLES__` WHERE table_id NOT LIKE 'ext_%') AS STRING), ' tables') AS detail
    UNION ALL
    SELECT 'silver: 4,939 matches, 4,589 finished, 350 scheduled',
           (SELECT COUNT(*) FROM `PROJECT.silver.matches`) = 4939
           AND (SELECT COUNTIF(status = 'finished') FROM `PROJECT.silver.matches`) = 4589,
           (SELECT CONCAT(COUNT(*), ' / ', COUNTIF(status = 'finished'), ' / ', COUNTIF(status = 'scheduled')) FROM `PROJECT.silver.matches`)
    UNION ALL
    SELECT 'gold: match_features has 4,939 rows and no G1 leak',
           (SELECT COUNT(*) FROM `PROJECT.gold.match_features`) = 4939
           AND (SELECT COUNT(*) FROM `PROJECT.gold.match_features` f,
                       UNNEST(ARRAY_CONCAT(f.home_history_match_ids, f.away_history_match_ids, f.extra_history_match_ids)) AS h
                       JOIN `PROJECT.silver.matches` m ON m.match_id = h WHERE m.kickoff_utc >= f.kickoff_utc) = 0,
           (SELECT CONCAT(COUNT(*), ' rows, computed ', FORMAT_TIMESTAMP('%d/%m %H:%M', MAX(computed_at))) FROM `PROJECT.gold.match_features`)
    UNION ALL
    SELECT 'models: 4 trained models present (query fails if any is missing)',
           (SELECT COUNT(*) FROM ML.TRAINING_INFO(MODEL `PROJECT.gold.outcome_model_v1`)) > 0
           AND (SELECT COUNT(*) FROM ML.TRAINING_INFO(MODEL `PROJECT.gold.outcome_model_v2`)) > 0
           AND (SELECT COUNT(*) FROM ML.TRAINING_INFO(MODEL `PROJECT.gold.goals_home_model`)) > 0
           AND (SELECT COUNT(*) FROM ML.TRAINING_INFO(MODEL `PROJECT.gold.goals_away_model`)) > 0,
           CONCAT('v2 trained in ', (SELECT MAX(iteration) + 1 FROM ML.TRAINING_INFO(MODEL `PROJECT.gold.outcome_model_v2`)), ' iterations')
    UNION ALL
    SELECT 'model answers live: ML.PREDICT on one scheduled match',
           (SELECT COUNT(*) FROM ML.PREDICT(MODEL `PROJECT.gold.outcome_model_v2`,
                 (SELECT * FROM `PROJECT.gold.match_features` WHERE split_set = 'PREDICT' LIMIT 1))) = 1,
           (SELECT CONCAT('predicted ', predicted_label_outcome) FROM ML.PREDICT(MODEL `PROJECT.gold.outcome_model_v2`,
                 (SELECT * FROM `PROJECT.gold.match_features` WHERE split_set = 'PREDICT' ORDER BY kickoff_utc LIMIT 1)))
    UNION ALL
    SELECT 'predictions: next fixture present and in the future',
           (SELECT MIN(kickoff_utc) FROM `PROJECT.gold.predictions_goals`) > CURRENT_TIMESTAMP(),
           (SELECT CONCAT(COUNT(*), ' fixtures, next on ', FORMAT_TIMESTAMP('%d/%m %H:%M', MIN(kickoff_utc))) FROM `PROJECT.gold.predictions_goals`)
    UNION ALL
    SELECT 'quality: report view answers and label split matches reference',
           (SELECT value FROM `PROJECT.quality.report` WHERE metric LIKE 'gold: label distribution%') = '44.3 / 31.8 / 23.9',
           (SELECT value FROM `PROJECT.quality.report` WHERE metric LIKE 'gold: label distribution%')
)
SELECT item, IF(ok, 'OK', 'FAIL') AS status, detail
FROM checks;
