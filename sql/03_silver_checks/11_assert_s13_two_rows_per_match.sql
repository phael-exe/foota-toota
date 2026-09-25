-- S13 (BLOCKING): team_matches holds exactly one row per club per match.
ASSERT (
    SELECT COUNT(*) = 2 * COUNT(DISTINCT match_id)
    FROM `PROJECT.silver.team_matches`
) AS 'S13: team_matches does not hold exactly two rows per match';
