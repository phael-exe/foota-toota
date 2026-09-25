-- S15 (BLOCKING): every raw position value must translate to a canonical code.
-- An untranslated value would silently become a NULL position.
ASSERT (
    SELECT COUNT(*) = 0
    FROM (
        SELECT DISTINCT position_raw
        FROM `PROJECT.silver.player_match_stats`
        WHERE position_raw IS NOT NULL
    ) p
    LEFT JOIN `PROJECT.silver.position_map` m
      ON m.raw = p.position_raw
    WHERE m.canonical IS NULL
) AS 'S15: position value missing from the translation table';
