-- External table for News RSS sports articles with full extracted text.
-- Format: JSON Lines. URI: gs://BUCKET/bronze/news_rss/dt=*/*.jsonl
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_news_rss`
OPTIONS (
    format = 'NEWLINE_DELIMITED_JSON',
    uris = ['gs://BUCKET/bronze/news_rss/*/*.jsonl'],
    ignore_unknown_values = true
);
