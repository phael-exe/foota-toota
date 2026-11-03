-- Sports news articles fact table with full body text.
-- Deduplicated by article URL / GUID.
-- Partitioned by DATE(published_at), clustered by source, language.

CREATE OR REPLACE TABLE `PROJECT.silver.news_articles`
PARTITION BY DATE(published_at)
CLUSTER BY source, language AS
WITH raw_news AS (
    SELECT
        FARM_FINGERPRINT(COALESCE(link, guid)) AS article_id,
        `PROJECT.silver.blank_to_null`(guid) AS guid,
        `PROJECT.silver.blank_to_null`(title) AS title,
        `PROJECT.silver.blank_to_null`(link) AS article_url,
        `PROJECT.silver.blank_to_null`(description) AS summary,
        `PROJECT.silver.blank_to_null`(content_body) AS content_body,
        SAFE_CAST(character_count AS INT64) AS character_count,
        COALESCE(
            SAFE_CAST(published_at AS TIMESTAMP),
            SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*SZ', published_at),
            SAFE.PARSE_TIMESTAMP('%a, %d %b %Y %H:%M:%S %Z', pub_date_raw)
        ) AS published_at,
        `PROJECT.silver.blank_to_null`(source) AS source,
        `PROJECT.silver.blank_to_null`(feed_topic) AS feed_topic,
        COALESCE(`PROJECT.silver.blank_to_null`(language), 'pt') AS language,
        SAFE_CAST(captured_at AS TIMESTAMP) AS captured_at,
        batch_id,
        source_file,
        ingested_at,
        ROW_NUMBER() OVER(
            PARTITION BY COALESCE(link, guid)
            ORDER BY ingested_at DESC
        ) AS rn
    FROM `PROJECT.bronze.news_rss`
    WHERE `PROJECT.silver.blank_to_null`(title) IS NOT NULL
)
SELECT
    article_id,
    guid,
    title,
    article_url,
    summary,
    content_body,
    character_count,
    published_at,
    source,
    feed_topic,
    language,
    captured_at,
    batch_id,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM raw_news
WHERE rn = 1;
