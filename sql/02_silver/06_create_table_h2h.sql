-- Head-to-head history (expected ~11,792 rows out of 40,079).
-- G2: 70.6% of the raw rows are dated on or after the match they were fetched for, and 3,267
--     of them are that match itself. Only strictly earlier meetings survive.
--     10 rows are duplicated on (for_match_id, match_id), hence the DISTINCT.
CREATE OR REPLACE TABLE `PROJECT.silver.h2h` AS
SELECT DISTINCT
    `PROJECT.silver.blank_to_null`(h.for_match_id) AS for_match_id,
    `PROJECT.silver.blank_to_null`(h.match_id) AS match_id,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(h.date) AS TIMESTAMP) AS match_date,
    `PROJECT.silver.blank_to_null`(h.home) AS home_name,
    `PROJECT.silver.blank_to_null`(h.away) AS away_name,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(h.home_score) AS INT64) AS home_score,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(h.away_score) AS INT64) AS away_score
FROM `PROJECT.bronze.stored_matches_h2h` h
JOIN `PROJECT.silver.matches` m
  ON m.match_id = `PROJECT.silver.blank_to_null`(h.for_match_id)
WHERE SAFE_CAST(`PROJECT.silver.blank_to_null`(h.date) AS TIMESTAMP) < m.kickoff_utc
  AND `PROJECT.silver.blank_to_null`(h.match_id) <> `PROJECT.silver.blank_to_null`(h.for_match_id);
