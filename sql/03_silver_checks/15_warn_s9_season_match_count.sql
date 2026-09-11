-- S9 (WARNING): every closed season should hold 380 matches.
-- In this batch 2020/21 holds 379: Leeds x Newcastle is missing from the source.
INSERT INTO `PROJECT.quality.occurrences` (rule, severity, row_count, detail, detected_at)
SELECT
    'S9',
    'WARNING',
    COUNT(*),
    STRING_AGG(CONCAT(CAST(season AS STRING), '=', CAST(matches AS STRING)), ', '),
    CURRENT_TIMESTAMP()
FROM (
    SELECT season, COUNT(*) AS matches
    FROM `PROJECT.silver.matches`
    WHERE season < (SELECT MAX(season) FROM `PROJECT.silver.matches`)
    GROUP BY season
    HAVING COUNT(*) <> 380
)
HAVING COUNT(*) > 0;
