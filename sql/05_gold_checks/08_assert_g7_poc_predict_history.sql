-- G7 (BLOCKING): fixtures to predict must reach their clubs' history. If most PREDICT rows
-- lack five earlier matches, team ids differ between the history and the fixture source.
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT league_id
        FROM `PROJECT.gold.match_features`
        WHERE league_id IN ('epl', 'brasileirao_serie_a') AND split_set = 'PREDICT'
        GROUP BY league_id
        HAVING COUNTIF(has_full_history) < 0.5 * COUNT(*)
    )
) AS 'G7: most PREDICT matches of a PoC league lack full history';
