-- S7 (QUARANTINE): SAFE_CAST returned NULL where the raw column held a value.
-- The pipeline carries on; the occurrence is recorded for the quality report.
INSERT INTO `PROJECT.quality.occurrences` (rule, severity, row_count, detail, detected_at)
SELECT
    'S7',
    'QUARANTINE',
    COUNT(*),
    'SAFE_CAST returned NULL for a non-null raw value',
    CURRENT_TIMESTAMP()
FROM `PROJECT.silver.matches`
WHERE (score_home_raw IS NOT NULL AND score_home  IS NULL)
   OR (score_away_raw IS NOT NULL AND score_away  IS NULL)
   OR (kickoff_raw    IS NOT NULL AND kickoff_utc IS NULL)
HAVING COUNT(*) > 0;
