-- Each club's form as it stood BEFORE each of its matches.
-- history_match_ids records which matches went into the numbers, so rule G1 stays verifiable.
CREATE OR REPLACE TABLE `PROJECT.gold.team_form` AS
WITH pairs AS (
    SELECT
        t.match_id,
        t.team_id,
        t.kickoff_utc,
        t.season,
        h.match_id AS hist_match_id,
        h.kickoff_utc AS hist_kickoff,
        h.season AS hist_season,
        h.points,
        h.goals_for,
        h.goals_against,
        ROW_NUMBER() OVER (
            PARTITION BY t.match_id, t.team_id
            ORDER BY h.kickoff_utc DESC
        ) AS rn
    FROM `PROJECT.silver.team_matches` t
    JOIN `PROJECT.silver.team_matches` h
      ON  h.team_id     = t.team_id
      AND h.status      = 'finished'
      AND h.kickoff_utc < t.kickoff_utc   -- strictly earlier: the whole point of the table
)
SELECT
    match_id,
    team_id,
    -- most recent first
    ARRAY_AGG(IF(rn <= 5, hist_match_id, NULL) IGNORE NULLS ORDER BY rn) AS history_match_ids,
    COUNTIF(rn <= 5) AS history_count,
    MIN(IF(rn <= 5, hist_kickoff, NULL)) AS history_oldest_kickoff_utc,
    MAX(IF(rn <= 5, hist_kickoff, NULL)) AS history_latest_kickoff_utc,
    AVG(IF(rn <= 5, points, NULL)) AS avg_points_last_5,
    AVG(IF(rn <= 5, goals_for, NULL)) AS avg_goals_for_last_5,
    AVG(IF(rn <= 5, goals_against, NULL)) AS avg_goals_against_last_5,
    -- season to date, not capped at five matches
    AVG(IF(hist_season = season, points, NULL)) AS avg_points_season,
    ARRAY_AGG(IF(hist_season = season, hist_match_id, NULL) IGNORE NULLS) AS season_match_ids,
    DATE_DIFF(DATE(ANY_VALUE(kickoff_utc)), DATE(MAX(hist_kickoff)), DAY) AS rest_days
FROM pairs
GROUP BY match_id, team_id;
