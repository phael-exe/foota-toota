-- In-match events. In this batch every row is a goal (event_type = 'Goal').
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_matches_events` (
    match_id      STRING,
    team          STRING,
    player_name   STRING,
    assist_name   STRING,
    event_type    STRING,
    event_detail  STRING,
    elapsed       STRING,
    elapsed_extra STRING
)
OPTIONS (
    format                = 'CSV',
    uris                  = ['gs://BUCKET/matches_events.csv'],
    skip_leading_rows     = 1,
    field_delimiter       = ',',
    quote                 = '"',
    allow_quoted_newlines = TRUE,
    encoding              = 'UTF-8'
);
