-- Where v2 gets it wrong, not just how often.
SELECT 'v2' AS model, *
FROM ML.CONFUSION_MATRIX(
    MODEL `PROJECT.gold.outcome_model_v2`,
    (SELECT * FROM `PROJECT.gold.test_set`)
);
