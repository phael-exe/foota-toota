-- Head-to-head history attached to each match (for_match_id is the match it was fetched for).
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_stored_matches_h2h` (
    for_match_id STRING,
    match_id     STRING,
    date         STRING,
    home         STRING,
    away         STRING,
    home_score   STRING,
    away_score   STRING
)
OPTIONS (
    format                = 'CSV',
    uris                  = ['gs://BUCKET/stored_matches_h2h.csv'],
    skip_leading_rows     = 1,
    field_delimiter       = ',',
    quote                 = '"',
    allow_quoted_newlines = TRUE,
    encoding              = 'UTF-8'
);
