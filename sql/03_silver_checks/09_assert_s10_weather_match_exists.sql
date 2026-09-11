-- S10 (BLOCKING): satellite tables may only reference matches that exist.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.match_weather` w
    WHERE NOT EXISTS (
        SELECT 1 FROM `PROJECT.silver.matches` m WHERE m.match_id = w.match_id
    )
) AS 'S10: satellite table references a match that does not exist';
