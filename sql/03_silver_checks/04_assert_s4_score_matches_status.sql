-- S4 (BLOCKING): a finished match has a score, a scheduled one does not, and no score is negative.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.matches`
    WHERE (status = 'finished'  AND (score_home IS NULL     OR score_away IS NULL))
       OR (status = 'scheduled' AND (score_home IS NOT NULL OR score_away IS NOT NULL))
       OR score_home < 0
       OR score_away < 0
) AS 'S4: score inconsistent with match status';
