-- G4 (BLOCKING): finished matches carry a label, scheduled ones must not.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.gold.match_features`
    WHERE (status = 'scheduled' AND label_outcome IS NOT NULL)
       OR (status = 'finished'  AND label_outcome IS NULL)
) AS 'G4: label inconsistent with match status';
