-- S1 (BLOCKING): match_id is the primary key of silver.matches.
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT match_id
        FROM `PROJECT.silver.matches`
        GROUP BY match_id
        HAVING COUNT(*) > 1
    )
) AS 'S1: duplicated match_id in silver.matches';
