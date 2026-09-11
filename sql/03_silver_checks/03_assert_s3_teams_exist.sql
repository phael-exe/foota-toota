-- S3 (BLOCKING): both clubs of a match must exist in silver.teams.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.matches` m
    WHERE NOT EXISTS (SELECT 1 FROM `PROJECT.silver.teams` t WHERE t.team_id = m.home_team_id)
       OR NOT EXISTS (SELECT 1 FROM `PROJECT.silver.teams` t WHERE t.team_id = m.away_team_id)
) AS 'S3: match references a club that does not exist';
