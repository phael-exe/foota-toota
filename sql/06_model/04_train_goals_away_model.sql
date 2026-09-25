-- Goal model, away side: expected away goals from the same 15 pre-match features.
CREATE OR REPLACE MODEL `PROJECT.gold.goals_away_model`
OPTIONS (
    model_type            = 'BOOSTED_TREE_REGRESSOR',
    input_label_cols      = ['away_goals'],
    data_split_method     = 'CUSTOM',
    data_split_col        = 'is_eval',
    max_iterations        = 50,
    max_tree_depth        = 3,
    early_stop            = TRUE,
    enable_global_explain = TRUE
) AS
SELECT
    CAST(m.score_away AS FLOAT64) AS away_goals,
    f.split_set = 'EVAL' AS is_eval,
    f.home_avg_points_last_5, f.home_avg_goals_for_last_5, f.home_avg_goals_against_last_5, f.home_avg_points_season, f.home_rest_days,
    f.away_avg_points_last_5, f.away_avg_goals_for_last_5, f.away_avg_goals_against_last_5, f.away_avg_points_season, f.away_rest_days,
    f.h2h_avg_points_last_5,
    f.diff_avg_points_last_5, f.diff_avg_goals_for_last_5, f.diff_avg_goals_against_last_5, f.diff_avg_points_season
FROM `PROJECT.gold.match_features` f
JOIN `PROJECT.silver.matches` m USING (match_id)
WHERE f.split_set IN ('TRAIN', 'EVAL')
  AND f.has_full_history
  AND m.status = 'finished';
