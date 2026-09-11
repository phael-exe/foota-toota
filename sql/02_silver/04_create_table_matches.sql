-- Matches, one row per match_id.
-- S1: 4,940 raw rows for 4,939 ids. The duplicate (Leicester x Everton, 2020-12-16) differs
--     only in starts_in_seconds, which is dropped, so SELECT DISTINCT over the analytical
--     columns collapses it safely.
-- S8: 10 fully empty columns dropped (season, *_abbreviation, *_flag_url, venue, updated_at,
--     winner, score, linescore). status_enum duplicates status; is_live, sport and league are
--     constant; starts_in_seconds is relative to extraction time.
-- S9: season is derived with a cut in AUGUST (the covid restart ran 2020-06-17 to 2020-07-26,
--     while 2020/21 only began on 2020-09-12).
CREATE OR REPLACE TABLE `PROJECT.silver.matches` AS
WITH deduplicated AS (
    SELECT DISTINCT
        `PROJECT.silver.blank_to_null`(id) AS match_id,
        LOWER(`PROJECT.silver.blank_to_null`(league)) AS league_id,
        `PROJECT.silver.blank_to_null`(home_id) AS home_team_id,
        `PROJECT.silver.blank_to_null`(away_id) AS away_team_id,
        `PROJECT.silver.blank_to_null`(kickoff_utc) AS kickoff_raw,
        LOWER(`PROJECT.silver.blank_to_null`(status)) AS status,
        `PROJECT.silver.blank_to_null`(score_home) AS score_home_raw,
        `PROJECT.silver.blank_to_null`(score_away) AS score_away_raw,
        `PROJECT.silver.blank_to_null`(linescore_home) AS linescore_home,
        `PROJECT.silver.blank_to_null`(linescore_away) AS linescore_away,
        `PROJECT.silver.blank_to_null`(attendance) AS attendance_raw,
        `PROJECT.silver.blank_to_null`(round) AS round,
        `PROJECT.silver.blank_to_null`(has_odds) AS has_odds_raw,
        batch_id,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.stored_matches`
),
typed AS (
    SELECT
        match_id,
        league_id,
        home_team_id,
        away_team_id,
        SAFE_CAST(kickoff_raw AS TIMESTAMP) AS kickoff_utc,
        status,
        SAFE_CAST(score_home_raw AS INT64) AS score_home,
        SAFE_CAST(score_away_raw AS INT64) AS score_away,
        linescore_home,
        linescore_away,
        SAFE_CAST(attendance_raw AS INT64) AS attendance,
        round,
        SAFE_CAST(has_odds_raw AS BOOL) AS has_odds,
        kickoff_raw,
        score_home_raw,
        score_away_raw,
        batch_id,
        source_file,
        ingested_at
    FROM deduplicated
)
SELECT
    match_id,
    league_id,
    home_team_id,
    away_team_id,
    kickoff_utc,
    IF(EXTRACT(MONTH FROM kickoff_utc) >= 8,
       EXTRACT(YEAR FROM kickoff_utc),
       EXTRACT(YEAR FROM kickoff_utc) - 1) AS season,
    status,
    score_home,
    score_away,
    CASE
        WHEN status = 'finished' AND score_home > score_away THEN 'home'
        WHEN status = 'finished' AND score_home = score_away THEN 'draw'
        WHEN status = 'finished' AND score_home < score_away THEN 'away'
    END AS outcome,
    linescore_home,
    linescore_away,
    attendance,
    round,
    has_odds,
    kickoff_raw,
    score_home_raw,
    score_away_raw,
    batch_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM typed;
