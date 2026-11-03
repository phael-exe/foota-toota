-- S23 (BLOCKING): stats and odds read from the right columns. BigQuery reads a CSV by position,
-- and the Football-Data.co.uk files differ by league and season, so a shifted file once put
-- shots in the referee column and the draw price in bet365_home_win for 7 leagues. Per league:
--   shots on target above shots in at most 1% of the games (the source has the odd typo)
--   the Bet365 favourite wins at least 35% of the finished games (about 45-50% is normal; a
--   shifted file gave about 22%)
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT m.league_id
        FROM `PROJECT.silver.match_stats` s
        JOIN `PROJECT.silver.matches` m USING (match_id)
        GROUP BY m.league_id
        HAVING COUNTIF(s.home_shots_on_target > s.home_shots
                       OR s.away_shots_on_target > s.away_shots) > 0.01 * COUNT(*)
        UNION ALL
        SELECT m.league_id
        FROM `PROJECT.silver.match_odds` o
        JOIN `PROJECT.silver.matches` m USING (match_id)
        WHERE m.status = 'finished'
          AND o.bet365_home_win IS NOT NULL AND o.bet365_away_win IS NOT NULL
        GROUP BY m.league_id
        HAVING COUNT(*) >= 100
           AND COUNTIF(IF(o.bet365_home_win < o.bet365_away_win,
                          m.outcome = 'home', m.outcome = 'away')) < 0.35 * COUNT(*)
    )
) AS 'S23: stats or odds out of place in a league (columns read by position?)';
