-- Head-to-head form: the last 5 meetings between the same two clubs, scored from the
-- home side's point of view. Built off team_matches so the strictly-earlier rule is shared.
CREATE OR REPLACE TABLE `PROJECT.gold.h2h_form` AS
WITH pairs AS (
    SELECT
        t.match_id,
        h.match_id AS hist_match_id,
        h.points,
        ROW_NUMBER() OVER (
            PARTITION BY t.match_id
            ORDER BY h.kickoff_utc DESC
        ) AS rn
    FROM `PROJECT.silver.team_matches` t
    JOIN `PROJECT.silver.team_matches` h
      ON  h.team_id     = t.team_id
      AND h.opponent_id = t.opponent_id
      AND h.status      = 'finished'
      AND h.kickoff_utc < t.kickoff_utc
    WHERE t.is_home
)
SELECT
    match_id,
    AVG(IF(rn <= 5, points, NULL)) AS h2h_avg_points_last_5,
    ARRAY_AGG(IF(rn <= 5, hist_match_id, NULL) IGNORE NULLS ORDER BY rn) AS h2h_match_ids
FROM pairs
GROUP BY match_id;
