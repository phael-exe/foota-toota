-- B1 (WARNING): every landed table must hold the row count the source file promised.
WITH expected AS (
    SELECT 'stored_matches'               AS table_name, 4940 AS expected_rows
    UNION ALL SELECT 'teams',                              36
    UNION ALL SELECT 'leagues',                             8
    UNION ALL SELECT 'players',                           775
    UNION ALL SELECT 'stored_matches_h2h',              40079
    UNION ALL SELECT 'matches_weather',                  4451
    UNION ALL SELECT 'matches_events',                  12879
    UNION ALL SELECT 'stored_matches_stats_players',    78006
)
SELECT
    e.table_name,
    e.expected_rows,
    t.row_count AS actual_rows,
    ROUND(t.size_bytes / 1048576, 1) AS size_mib,
    IF(e.expected_rows = t.row_count, 'OK', 'MISMATCH') AS b1
FROM expected e
JOIN `PROJECT.bronze.__TABLES__` t
  ON t.table_id = e.table_name
ORDER BY e.expected_rows DESC;
