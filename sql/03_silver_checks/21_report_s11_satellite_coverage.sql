-- S11: how much of the finished matches each satellite table covers.
-- Reference for this batch: weather 97.0 - goals 93.6 - player_stats 91.7.
SELECT
    'weather' AS satellite,
    ROUND(100 * COUNT(DISTINCT w.match_id)
          / (SELECT COUNTIF(status = 'finished') FROM `PROJECT.silver.matches`), 1) AS coverage_pct,
    97.0 AS reference_pct
FROM `PROJECT.silver.match_weather` w
JOIN `PROJECT.silver.matches` m
  ON m.match_id = w.match_id AND m.status = 'finished'
UNION ALL
SELECT
    'goals',
    ROUND(100 * COUNT(DISTINCT g.match_id)
          / (SELECT COUNTIF(status = 'finished') FROM `PROJECT.silver.matches`), 1),
    93.6
FROM `PROJECT.silver.match_goals` g
JOIN `PROJECT.silver.matches` m
  ON m.match_id = g.match_id AND m.status = 'finished'
UNION ALL
SELECT
    'player_stats',
    ROUND(100 * COUNT(DISTINCT s.match_id)
          / (SELECT COUNTIF(status = 'finished') FROM `PROJECT.silver.matches`), 1),
    91.7
FROM `PROJECT.silver.player_match_stats` s
JOIN `PROJECT.silver.matches` m
  ON m.match_id = s.match_id AND m.status = 'finished';
