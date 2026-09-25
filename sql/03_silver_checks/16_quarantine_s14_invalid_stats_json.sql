-- S14 (QUARANTINE): stats_json that does not parse. Expected count: 0.
INSERT INTO `PROJECT.quality.occurrences` (rule, severity, row_count, detail, detected_at)
SELECT
    'S14',
    'QUARANTINE',
    COUNT(*),
    'invalid stats_json',
    CURRENT_TIMESTAMP()
FROM `PROJECT.silver.player_match_stats`
WHERE stats_json IS NOT NULL
  AND SAFE.PARSE_JSON(stats_json) IS NULL
HAVING COUNT(*) > 0;
