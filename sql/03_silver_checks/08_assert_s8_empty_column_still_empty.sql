-- S8 (BLOCKING): score was dropped as 100% empty. If it ever carries data, the data
-- dictionary is out of date and the silver schema has to be revisited.
ASSERT (
    SELECT COUNTIF(score IS NOT NULL) = 0
    FROM `PROJECT.bronze.stored_matches`
) AS 'S8: a column documented as empty (score) holds data; review the dictionary';
