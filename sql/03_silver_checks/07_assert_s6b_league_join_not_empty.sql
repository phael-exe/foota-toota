-- S6b (BLOCKING): S6 alone would also pass if the join silently returned nothing.
ASSERT (
    SELECT COUNT(*) > 0
    FROM `PROJECT.silver.matches` m
    JOIN `PROJECT.silver.leagues` l USING (league_id)
) AS 'S6b: the competition join returned no rows';
