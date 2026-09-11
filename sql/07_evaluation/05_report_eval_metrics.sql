-- What BigQuery ML measured on the eval split during training.
-- Compare against the test numbers: a large gap is overfitting.
SELECT
    'v1 (eval split)' AS model,
    ROUND(accuracy, 4) AS accuracy,
    ROUND(log_loss, 4) AS log_loss
FROM ML.EVALUATE(MODEL `PROJECT.gold.outcome_model_v1`)
UNION ALL
SELECT
    'v2 (eval split)',
    ROUND(accuracy, 4),
    ROUND(log_loss, 4)
FROM ML.EVALUATE(MODEL `PROJECT.gold.outcome_model_v2`);
