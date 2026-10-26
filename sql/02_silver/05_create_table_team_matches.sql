-- One row per club per match (2 rows per match), so form can be computed with a single scan.
-- Points are 3/1/0 on finished matches only; NULL on scheduled ones.
-- Partitioned by DATE(kickoff_utc), clustered by league_id, team_id.
CREATE OR REPLACE TABLE `PROJECT.silver.team_matches`
PARTITION BY DATE(kickoff_utc)
CLUSTER BY league_id, team_id, opponent_id AS
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
    away_team_id AS team_id,
    home_team_id AS opponent_id,
    FALSE AS is_home,
    score_away AS goals_for,
    score_home AS goals_against,
    CASE WHEN status = 'finished' THEN
        CASE
            WHEN score_away > score_home THEN 3
            WHEN score_away = score_home THEN 1
            ELSE 0
        END
    END AS points,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.silver.matches`;
