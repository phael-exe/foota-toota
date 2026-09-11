-- S5 (BLOCKING): only two statuses exist in this batch. A third one means the vocabulary changed.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.matches`
    WHERE status NOT IN ('finished', 'scheduled')
) AS 'S5: unknown match status';
