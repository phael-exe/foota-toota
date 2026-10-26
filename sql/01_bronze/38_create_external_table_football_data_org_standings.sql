-- External table for Football-Data.org API standings tables.
-- Format: JSON Lines. URI: gs://BUCKET/bronze/football_data_org_standings/competition=*/*.jsonl
-- The league table and the season stay JSON, which silver reads with JSON_EXTRACT_ARRAY and
-- JSON_VALUE; autodetect would turn them into STRUCTs, as in the matches table.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_org_standings` (
    `stage`             STRING,
    `type`              STRING,
    `group`             STRING,
    `table`             JSON,
    `_competition_code` STRING,
    `_competition_name` STRING,
    `_season`           JSON
)
OPTIONS (
    format = 'NEWLINE_DELIMITED_JSON',
    uris = ['gs://BUCKET/bronze/football_data_org_standings/*'],
    ignore_unknown_values = true
);
