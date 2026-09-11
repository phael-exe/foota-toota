-- Section 7 of the validation rules: the quality report, republished on every pipeline run.
-- Each row pairs what this run measured against the reference value agreed for this batch.
CREATE OR REPLACE VIEW `PROJECT.quality.report` AS
SELECT 'bronze: stored_matches rows' AS metric,
       CAST(COUNT(*) AS STRING) AS value,
       '4,940' AS reference
FROM `PROJECT.bronze.stored_matches`
UNION ALL
SELECT 'silver: matches after deduplication',
       CAST(COUNT(*) AS STRING),
       '4,939'
FROM `PROJECT.silver.matches`
UNION ALL
SELECT 'silver: finished / scheduled',
       CONCAT(COUNTIF(status = 'finished'), ' / ', COUNTIF(status = 'scheduled')),
       '4,589 / 350'
FROM `PROJECT.silver.matches`
UNION ALL
SELECT 'silver: closed seasons not holding 380 matches',
       CAST(COUNT(*) AS STRING),
       '1 (2020/21 = 379: Leeds x Newcastle missing)'
FROM (
    SELECT season
    FROM `PROJECT.silver.matches`
    WHERE season < (SELECT MAX(season) FROM `PROJECT.silver.matches`)
    GROUP BY season
    HAVING COUNT(*) <> 380
)
UNION ALL
SELECT 'silver: coverage weather / goals / player_stats (%)',
       CONCAT(
           (SELECT ROUND(100 * COUNT(DISTINCT match_id) / 4589, 1) FROM `PROJECT.silver.match_weather`), ' / ',
           (SELECT ROUND(100 * COUNT(DISTINCT match_id) / 4589, 1) FROM `PROJECT.silver.match_goals`), ' / ',
           (SELECT ROUND(100 * COUNT(DISTINCT match_id) / 4589, 1) FROM `PROJECT.silver.player_match_stats`)
       ),
       '97.0 / 93.6 / 91.7'
UNION ALL
SELECT 'silver: h2h rows dropped by the time filter',
       CONCAT(
           CAST((SELECT COUNT(*) FROM `PROJECT.bronze.stored_matches_h2h`) - COUNT(*) AS STRING),
           ' (',
           CAST(ROUND(100 - 100 * COUNT(*)
                / (SELECT COUNT(*) FROM `PROJECT.bronze.stored_matches_h2h`), 1) AS STRING),
           '%)'
       ),
       '28,287 (70.6%)'
FROM `PROJECT.silver.h2h`
UNION ALL
SELECT 'silver: quarantined cast failures',
       CAST(COUNT(*) AS STRING),
       '0'
FROM `PROJECT.silver.matches`
WHERE (score_home_raw IS NOT NULL AND score_home  IS NULL)
   OR (score_away_raw IS NOT NULL AND score_away  IS NULL)
   OR (kickoff_raw    IS NOT NULL AND kickoff_utc IS NULL)
UNION ALL
SELECT 'silver: columns promoted (all tables)',
       CAST(COUNT(*) AS STRING),
       '<= 273'
FROM `PROJECT.silver.INFORMATION_SCHEMA.COLUMNS`
UNION ALL
SELECT 'gold: label distribution home / away / draw (%)',
       CONCAT(
           ROUND(100 * COUNTIF(label_outcome = 'home') / COUNT(*), 1), ' / ',
           ROUND(100 * COUNTIF(label_outcome = 'away') / COUNT(*), 1), ' / ',
           ROUND(100 * COUNTIF(label_outcome = 'draw') / COUNT(*), 1)
       ),
       '44.3 / 31.8 / 23.9'
FROM `PROJECT.gold.match_features`
WHERE status = 'finished'
UNION ALL
SELECT 'gold: matches per split (train / eval / test / predict)',
       CONCAT(
           COUNTIF(split_set = 'TRAIN'),   ' / ',
           COUNTIF(split_set = 'EVAL'),    ' / ',
           COUNTIF(split_set = 'TEST'),    ' / ',
           COUNTIF(split_set = 'PREDICT')
       ),
       '3,799 / 380 / 410 / 350'
FROM `PROJECT.gold.match_features`
UNION ALL
SELECT 'gold: G1 leaks detected',
       CAST(COUNT(*) AS STRING),
       '0'
FROM `PROJECT.gold.match_features` f,
     UNNEST(ARRAY_CONCAT(
         f.home_history_match_ids,
         f.away_history_match_ids,
         f.extra_history_match_ids
     )) AS hist_id
JOIN `PROJECT.silver.matches` h
  ON h.match_id = hist_id
WHERE h.kickoff_utc >= f.kickoff_utc;
