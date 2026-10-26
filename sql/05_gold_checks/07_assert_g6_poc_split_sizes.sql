-- G6 (BLOCKING): each PoC league needs a whole season in EVAL and in TEST, or the
-- held-out metrics mean nothing (Brasileirao once had a single TEST match).
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT league_id
        FROM `PROJECT.gold.match_features`
        WHERE league_id IN ('epl', 'brasileirao_serie_a')
        GROUP BY league_id
        HAVING COUNTIF(split_set = 'EVAL') < 300 OR COUNTIF(split_set = 'TEST') < 300
    )
) AS 'G6: PoC league with fewer than 300 EVAL or TEST matches';
