-- v1: multiclass logistic regression, the baseline model the evaluation compares against.
-- Only matches with a full five-match history for both sides, so no row is fed to the model
-- with half its attributes missing.
-- The split is CUSTOM, driven by split_set, because an automatic split would mix seasons and
-- leak the future into training (rule C5).
CREATE OR REPLACE MODEL `PROJECT.gold.outcome_model_v1`
OPTIONS (
    model_type            = 'LOGISTIC_REG',
    input_label_cols      = ['label_outcome'],
    data_split_method     = 'CUSTOM',
    data_split_col        = 'is_eval',
    max_iterations        = 50,
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
