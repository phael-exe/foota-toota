-- S5 (BLOCKING): only standardized documented match statuses exist.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.matches`
    WHERE status NOT IN ('finished', 'scheduled', 'postponed', 'in_play', 'cancelled')
) AS 'S5: unknown match status';
