-- External table for Fantasy Premier League gameweeks (109k rows, 2021-2025).
-- URI: gs://BUCKET/bronze/fpl_gameweeks/*/*.csv
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_fpl_gameweeks`
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/fpl_gameweeks/*'],
    skip_leading_rows = 1,
    ignore_unknown_values = true
);
