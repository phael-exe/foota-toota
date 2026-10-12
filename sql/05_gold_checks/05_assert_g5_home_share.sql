-- G5 (BLOCKING): home advantage holds in every league and source. Measured per league and
-- source because the leagues differ (EPL home 44.3 / away 31.8, Brasileirao 49.6 / 24.0), so
-- one global reference drifts as leagues are added. A source whose away side wins more than
-- its home side, or about as often, most likely has home and away swapped upstream.
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT m.league_id, m.source_id
        FROM `PROJECT.gold.match_features` f
        JOIN `PROJECT.silver.matches` m USING (match_id)
        WHERE f.status = 'finished'
        GROUP BY m.league_id, m.source_id
        HAVING COUNT(*) >= 300
           AND 100 * (COUNTIF(f.label_outcome = 'home') - COUNTIF(f.label_outcome = 'away'))
               / COUNT(*) < 5
    )
) AS 'G5: home side not ahead of the away side in a league/source (home and away swapped?)';
