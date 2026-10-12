-- S21 (BLOCKING): no season is missing in a PoC league. Measured on kickoff dates, not on
-- the season column, so a NULL season cannot hide the hole: consecutive matches of a league
-- are never more than 300 days apart (the longest real break, Covid 2019->2020, was 244).
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT
            league_id,
            DATE_DIFF(
                DATE(kickoff_utc),
                DATE(LAG(kickoff_utc) OVER (PARTITION BY league_id ORDER BY kickoff_utc)),
                DAY
            ) AS gap_days
        FROM `PROJECT.silver.matches`
        WHERE league_id IN ('epl', 'brasileirao_serie_a')
    )
    WHERE gap_days > 300
) AS 'S21: PoC league with a missing season (gap over 300 days between matches)';
