-- S20 (BLOCKING): the PoC leagues are 20-club double round robins since 2006, so a season
-- never holds more than 380 matches and is never NULL. More means two sources were merged
-- without dedup (e.g. the same fixture under Big Balls and Football-Data.org ids).
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT league_id, season
        FROM `PROJECT.silver.matches`
        WHERE league_id IN ('epl', 'brasileirao_serie_a')
        GROUP BY league_id, season
        HAVING season IS NULL OR (season >= 2006 AND COUNT(*) > 380)
    )
) AS 'S20: PoC league season with NULL id or more than 380 matches';
