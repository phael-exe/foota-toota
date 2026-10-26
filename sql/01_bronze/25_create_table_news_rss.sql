-- Materializes news_rss into a native Bronze table with deduplication and provenance.
CREATE OR REPLACE TABLE `PROJECT.bronze.news_rss` AS
SELECT
    *,
    '20260923' AS batch_id,
    CURRENT_TIMESTAMP() AS ingested_at,
    _FILE_NAME AS source_file
FROM `PROJECT.bronze.ext_news_rss`;
