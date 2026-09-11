-- The bar to clear: always predict the majority class of the training data ('home').
-- A model that does not beat this number has learned nothing.
SELECT
    'baseline (always home)' AS model,
    COUNT(*) AS test_matches,
    ROUND(COUNTIF(label_outcome = 'home') / COUNT(*), 4) AS accuracy
FROM `PROJECT.gold.test_set`;
