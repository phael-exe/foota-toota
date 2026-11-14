-- S24 (WARNING): in the current season of a league, once one game has a round, every game has one.
-- The Football-Data.co.uk files carry no round, and a finished game kept from them takes it from
-- the Football-Data.org row of the same fixture (silver.matches). A game left without it shows up
-- with no round on the platform. Belgium and Scotland have no source with rounds, so no game there
-- has one and the rule leaves them out. Not blocking: a missing round should not hold the export.
INSERT INTO `PROJECT.quality.occurrences` (rule, severity, row_count, detail, detected_at)
SELECT
    'S24',
    'WARNING',
    SUM(sem_rodada),
    STRING_AGG(CONCAT(league_id, ' ', CAST(season AS STRING), '=', CAST(sem_rodada AS STRING)), ', '),
    CURRENT_TIMESTAMP()
FROM (
    SELECT league_id, season, COUNTIF(round IS NULL) AS sem_rodada
    FROM `PROJECT.silver.matches` AS m
    WHERE season = (
        SELECT MAX(season) FROM `PROJECT.silver.matches` WHERE league_id = m.league_id
    )
    GROUP BY league_id, season
    HAVING COUNTIF(round IS NULL) > 0 AND COUNTIF(round IS NOT NULL) > 0
)
HAVING COUNT(*) > 0;
