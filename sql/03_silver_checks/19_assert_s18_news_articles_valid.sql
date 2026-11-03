-- S18 (BLOCKING): news articles must have valid titles and published timestamps.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.news_articles`
    WHERE title IS NULL
       OR published_at IS NULL
       OR character_count <= 0
) AS 'S18: corrupted or empty news articles found in silver.news_articles';
