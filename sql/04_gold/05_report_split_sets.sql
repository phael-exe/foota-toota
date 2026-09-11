-- How the feature table divides into train, eval, test and predict.
SELECT
    split_set,
    COUNT(*) AS matches,
    COUNTIF(has_full_history) AS with_full_history,
    MIN(DATE(kickoff_utc)) AS first_kickoff,
    MAX(DATE(kickoff_utc)) AS last_kickoff
FROM `PROJECT.gold.match_features`
GROUP BY split_set
ORDER BY first_kickoff;
