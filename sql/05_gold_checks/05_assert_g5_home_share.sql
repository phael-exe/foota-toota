-- G5 (BLOCKING): the home side wins 44.3% of the matches in this batch. A large drift means
-- home and away were most likely swapped somewhere upstream.
ASSERT (
    SELECT ABS(100 * COUNTIF(label_outcome = 'home') / COUNT(*) - 44.3) < 2
    FROM `PROJECT.gold.match_features`
    WHERE status = 'finished'
) AS 'G5: home share far from the 44.3% reference (home and away swapped?)';
