-- The held-out set: matches from 2025-07 onwards, which neither model saw during training.
-- A view, not a table: it is only a filter over match_features, so it can never drift from the gold.
-- Same minimum-history filter as the training query, so the comparison is like for like.
CREATE OR REPLACE VIEW `PROJECT.gold.test_set` AS
SELECT *
FROM `PROJECT.gold.match_features`
WHERE split_set = 'TEST'
  AND has_full_history;
