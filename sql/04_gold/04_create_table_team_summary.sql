-- Descriptive aggregate: points won per club and season, split home and away.
-- Not a model input; this is the table the report and the slides read from.
CREATE OR REPLACE TABLE `PROJECT.gold.team_summary` AS
SELECT
    tm.season,
    t.team_name,
    COUNT(*) AS matches_played,
    COUNTIF(tm.points = 3) AS wins,
    COUNTIF(tm.points = 1) AS draws,
    COUNTIF(tm.points = 0) AS losses,
    SUM(tm.points) AS points,
    SUM(tm.goals_for) AS goals_for,
    SUM(tm.goals_against) AS goals_against,
    ROUND(100 * SUM(IF(tm.is_home, tm.points, 0))
          / (3 * COUNTIF(tm.is_home)), 1) AS home_points_pct,
    ROUND(100 * SUM(IF(NOT tm.is_home, tm.points, 0))
          / (3 * COUNTIF(NOT tm.is_home)), 1) AS away_points_pct
FROM `PROJECT.silver.team_matches` tm
JOIN `PROJECT.silver.teams` t USING (team_id)
WHERE tm.status = 'finished'
GROUP BY tm.season, t.team_name;
