-- S9 in detail: the match count behind the warning, season by season.
SELECT
    season,
    COUNT(*) AS matches,
    COUNTIF(status = 'finished') AS finished,
    COUNTIF(status = 'scheduled') AS scheduled
FROM `PROJECT.silver.matches`
GROUP BY season
ORDER BY season;
