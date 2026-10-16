-- External table for Football-Data.org API standings tables.
-- Format: JSON Lines. URI: gs://BUCKET/bronze/football_data_org_standings/*/*.jsonl
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_org_standings`
OPTIONS (
    format = 'NEWLINE_DELIMITED_JSON',
    uris = ['gs://BUCKET/bronze/football_data_org_standings/*'],
    ignore_unknown_values = true
);
