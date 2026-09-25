-- The feature table: one row per match (4,939 = 4,589 finished with a label + 350 scheduled).
-- Every attribute is computed ONLY from finished matches that kicked off STRICTLY earlier.
-- The *_history_match_ids columns name those matches, which is what makes rule G1 checkable.
CREATE OR REPLACE TABLE `PROJECT.gold.match_features` AS
SELECT
    -- identification: never fed to the model
    m.match_id,
    m.league_id,
    m.home_team_id,
    m.away_team_id,
    m.kickoff_utc,
    m.status,
    m.season,

    -- home side: auditable history
    COALESCE(hf.history_match_ids, []) AS home_history_match_ids,
    COALESCE(hf.history_count, 0) AS home_history_count,
    hf.history_oldest_kickoff_utc AS home_history_oldest_kickoff_utc,
    hf.history_latest_kickoff_utc AS home_history_latest_kickoff_utc,
    hf.avg_points_last_5 AS home_avg_points_last_5,
    hf.avg_goals_for_last_5 AS home_avg_goals_for_last_5,
    hf.avg_goals_against_last_5 AS home_avg_goals_against_last_5,

    -- away side: auditable history
    COALESCE(af.history_match_ids, []) AS away_history_match_ids,
    COALESCE(af.history_count, 0) AS away_history_count,
    af.history_oldest_kickoff_utc AS away_history_oldest_kickoff_utc,
    af.history_latest_kickoff_utc AS away_history_latest_kickoff_utc,
    af.avg_points_last_5 AS away_avg_points_last_5,
    af.avg_goals_for_last_5 AS away_avg_goals_for_last_5,
    af.avg_goals_against_last_5 AS away_avg_goals_against_last_5,

    -- differences, always home minus away
    hf.avg_points_last_5        - af.avg_points_last_5 AS diff_avg_points_last_5,
    hf.avg_goals_for_last_5     - af.avg_goals_for_last_5 AS diff_avg_goals_for_last_5,
    hf.avg_goals_against_last_5 - af.avg_goals_against_last_5 AS diff_avg_goals_against_last_5,

    -- season form, rest and head-to-head
    hf.avg_points_season AS home_avg_points_season,
    af.avg_points_season AS away_avg_points_season,
    hf.avg_points_season - af.avg_points_season AS diff_avg_points_season,
    LEAST(hf.rest_days, 60) AS home_rest_days,
    LEAST(af.rest_days, 60) AS away_rest_days,
    h.h2h_avg_points_last_5,
    ARRAY_CONCAT(
        COALESCE(hf.season_match_ids, []),
        COALESCE(af.season_match_ids, []),
        COALESCE(h.h2h_match_ids, [])
    ) AS extra_history_match_ids,

    -- filter, label, split and metadata
    COALESCE(hf.history_count, 0) = 5
        AND COALESCE(af.history_count, 0) = 5 AS has_full_history,
    m.outcome AS label_outcome,
    CASE
        WHEN m.status = 'scheduled'                  THEN 'PREDICT'
        WHEN m.kickoff_utc < TIMESTAMP('2024-07-01') THEN 'TRAIN'
        WHEN m.kickoff_utc < TIMESTAMP('2025-07-01') THEN 'EVAL'
        ELSE 'TEST'
    END AS split_set,   -- C5: split by date, never at random
    CURRENT_TIMESTAMP() AS computed_at
FROM `PROJECT.silver.matches` m
LEFT JOIN `PROJECT.gold.team_form` hf
       ON hf.match_id = m.match_id AND hf.team_id = m.home_team_id
LEFT JOIN `PROJECT.gold.team_form` af
       ON af.match_id = m.match_id AND af.team_id = m.away_team_id
LEFT JOIN `PROJECT.gold.h2h_form` h
       ON h.match_id = m.match_id;
