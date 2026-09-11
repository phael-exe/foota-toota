-- Feature importance for v1. This describes how the model reads the data;
-- it is not a claim about football.
SELECT
    'v1' AS model,
    feature,
    ROUND(attribution, 4) AS attribution
FROM ML.GLOBAL_EXPLAIN(MODEL `PROJECT.gold.outcome_model_v1`)
ORDER BY attribution DESC
LIMIT 8;
