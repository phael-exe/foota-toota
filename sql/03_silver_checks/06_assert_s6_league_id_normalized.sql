-- S6 (BLOCKING): league_id is lowercase everywhere, so joins never depend on casing.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.matches`
    WHERE league_id <> LOWER(league_id)
) AS 'S6: league_id is not normalized to lowercase';
