-- S16 (BLOCKING): all betting odds must be strictly greater than 1.0.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.match_odds`
    WHERE (bet365_home_win IS NOT NULL AND bet365_home_win <= 1.0)
       OR (bet365_draw IS NOT NULL AND bet365_draw <= 1.0)
       OR (bet365_away_win IS NOT NULL AND bet365_away_win <= 1.0)
       OR (pinnacle_home_win IS NOT NULL AND pinnacle_home_win <= 1.0)
       OR (pinnacle_draw IS NOT NULL AND pinnacle_draw <= 1.0)
       OR (pinnacle_away_win IS NOT NULL AND pinnacle_away_win <= 1.0)
) AS 'S16: found non-positive or invalid odds (<= 1.0) in silver.match_odds';
