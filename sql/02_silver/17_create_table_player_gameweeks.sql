-- Fantasy Premier League player gameweek performance fact table (109k+ player-match rows).
-- Detailed metrics: xG, xA, minutes, points, ICT index (2021-2025).
-- Partitioned by DATE(kickoff_time), clustered by season, team.

CREATE OR REPLACE TABLE `PROJECT.silver.player_gameweeks`
PARTITION BY DATE(kickoff_time)
CLUSTER BY season, team, player_name AS
SELECT
    `PROJECT.silver.blank_to_null`(name) AS player_name,
    `PROJECT.silver.blank_to_null`(position) AS position,
    `PROJECT.silver.blank_to_null`(team) AS team,
    `PROJECT.silver.blank_to_null`(season) AS season,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(round) AS INT64) AS gameweek,
    SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', kickoff_time) AS kickoff_time,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(minutes) AS INT64) AS minutes_played,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(goals_scored) AS INT64) AS goals_scored,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(assists) AS INT64) AS assists,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(clean_sheets) AS INT64) AS clean_sheets,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(goals_conceded) AS INT64) AS goals_conceded,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(expected_goals) AS FLOAT64) AS expected_goals_xg,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(expected_assists) AS FLOAT64) AS expected_assists_xa,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(expected_goal_involvements) AS FLOAT64) AS expected_goal_involvements_xgi,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(ict_index) AS FLOAT64) AS ict_index,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(influence) AS FLOAT64) AS influence,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(creativity) AS FLOAT64) AS creativity,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(threat) AS FLOAT64) AS threat,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(total_points) AS INT64) AS total_points,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(bonus) AS INT64) AS bonus_points,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(bps) AS INT64) AS bps,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(was_home) AS BOOL) AS was_home,
    `PROJECT.silver.blank_to_null`(opponent_team) AS opponent_team,
    batch_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.fpl_gameweeks`
WHERE `PROJECT.silver.blank_to_null`(name) IS NOT NULL;
