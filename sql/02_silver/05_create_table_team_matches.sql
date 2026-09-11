-- One row per club per match (9,878 = 2 x 4,939), so form can be computed with a single scan.
-- Points are 3/1/0 on finished matches only; NULL on scheduled ones. Never 0 for a scheduled
-- match, because 0 is a real result.
CREATE OR REPLACE TABLE `PROJECT.silver.team_matches` AS
SELECT
    match_id,
    league_id,
    season,
    kickoff_utc,
    status,
    home_team_id AS team_id,
    away_team_id AS opponent_id,
    TRUE AS is_home,
    score_home AS goals_for,
    score_away AS goals_against,
    CASE WHEN status = 'finished' THEN
        CASE
            WHEN score_home > score_away THEN 3
            WHEN score_home = score_away THEN 1
            ELSE 0
        END
    END AS points,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.silver.matches`
UNION ALL
SELECT
    match_id,
    league_id,
    season,
    kickoff_utc,
    status,
    away_team_id,
    home_team_id,
    FALSE,
    score_away,
    score_home,
    CASE WHEN status = 'finished' THEN
        CASE
            WHEN score_away > score_home THEN 3
            WHEN score_away = score_home THEN 1
            ELSE 0
        END
    END,
    CURRENT_TIMESTAMP()
FROM `PROJECT.silver.matches`;
