-- Both models on the held-out test set.
SELECT
    'v1 LOGISTIC_REG' AS model,
    ROUND(accuracy, 4) AS accuracy,
    ROUND(log_loss, 4) AS log_loss,
    ROUND(precision, 4) AS precision_macro,
    ROUND(recall, 4) AS recall_macro,
    ROUND(f1_score, 4) AS f1_macro
FROM ML.EVALUATE(
    MODEL `PROJECT.gold.outcome_model_v1`,
    (SELECT * FROM `PROJECT.gold.test_set`)
)
UNION ALL
SELECT
    'v2 BOOSTED_TREE',
    ROUND(accuracy, 4),
    ROUND(log_loss, 4),
    ROUND(precision, 4),
    ROUND(recall, 4),
    ROUND(f1_score, 4)
FROM ML.EVALUATE(
    MODEL `PROJECT.gold.outcome_model_v2`,
    (SELECT * FROM `PROJECT.gold.test_set`)
);
