-- v2: boosted trees over exactly the same SELECT as v1. Only the algorithm changes, so any
-- difference in the metrics is the algorithm and nothing else.
-- Shallow trees and early stopping on the eval split, to keep it from memorizing ~3,700 rows.
-- Boosted trees are not deterministic: run this more than once before claiming v2 won by a
-- narrow margin.
CREATE OR REPLACE MODEL `PROJECT.gold.outcome_model_v2`
OPTIONS (
    model_type            = 'BOOSTED_TREE_CLASSIFIER',
    input_label_cols      = ['label_outcome'],
    data_split_method     = 'CUSTOM',
    data_split_col        = 'is_eval',
    max_iterations        = 50,
    max_tree_depth        = 3,
    early_stop            = TRUE,
    enable_global_explain = TRUE
) AS
SELECT
    label_outcome,
    split_set = 'EVAL' AS is_eval,
    home_avg_points_last_5,
    home_avg_goals_for_last_5,
    home_avg_goals_against_last_5,
    home_avg_points_season,
    home_rest_days,
    away_avg_points_last_5,
    away_avg_goals_for_last_5,
    away_avg_goals_against_last_5,
    away_avg_points_season,
    away_rest_days,
    h2h_avg_points_last_5,
    diff_avg_points_last_5,
    diff_avg_goals_for_last_5,
    diff_avg_goals_against_last_5,
    diff_avg_points_season
FROM `PROJECT.gold.match_features`
WHERE split_set IN ('TRAIN', 'EVAL')
  AND has_full_history;
