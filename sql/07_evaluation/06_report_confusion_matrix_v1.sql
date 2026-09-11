-- Where v1 gets it wrong, not just how often.
SELECT 'v1' AS model, *
FROM ML.CONFUSION_MATRIX(
    MODEL `PROJECT.gold.outcome_model_v1`,
    (SELECT * FROM `PROJECT.gold.test_set`)
);
