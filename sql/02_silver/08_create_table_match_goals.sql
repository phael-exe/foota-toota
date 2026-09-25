-- Goals (12,879 rows). matches_events carries nothing but goals in this batch
-- (event_type = 'Goal' on 100% of the rows), so the table is named for what it holds.
-- There is no event id, so the 2 exactly duplicated rows are kept rather than guessed away.
CREATE OR REPLACE TABLE `PROJECT.silver.match_goals` AS
SELECT
    `PROJECT.silver.blank_to_null`(match_id) AS match_id,
    `PROJECT.silver.blank_to_null`(team) AS team_name,
    `PROJECT.silver.blank_to_null`(player_name) AS player_name,
    `PROJECT.silver.blank_to_null`(assist_name) AS assist_name,
    `PROJECT.silver.blank_to_null`(event_detail) AS goal_type,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(elapsed) AS INT64) AS elapsed,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(elapsed_extra) AS INT64) AS elapsed_extra
FROM `PROJECT.bronze.matches_events`;
