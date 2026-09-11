-- G5 in detail. Reference for this batch: home 44.3 - away 31.8 - draw 23.9.
SELECT
    label_outcome,
    COUNT(*) AS matches,
    ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM `PROJECT.gold.match_features`
WHERE status = 'finished'
GROUP BY label_outcome
ORDER BY matches DESC;
