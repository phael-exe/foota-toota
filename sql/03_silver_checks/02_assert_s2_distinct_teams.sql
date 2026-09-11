-- S2 (BLOCKING): a club cannot play itself.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.matches`
    WHERE home_team_id = away_team_id
) AS 'S2: match with the same club at home and away';
