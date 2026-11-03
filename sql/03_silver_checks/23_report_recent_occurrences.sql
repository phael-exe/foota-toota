-- Everything quarantined or warned about by this run.
SELECT rule, severity, row_count, detail
FROM `PROJECT.quality.occurrences`
WHERE detected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)
ORDER BY rule;
