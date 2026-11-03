-- S22 (BLOCKING): every club whose games overlap another source's games reaches that source
-- under one team_id (silver.team_map). A club left out would show twice in silver.matches, once
-- per source, and its page would split its games. Fix: a row in silver.team_alias.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.team_map`
    WHERE unresolved
) AS 'S22: club with games in two sources but no shared team_id (see silver.team_map.unresolved)';
