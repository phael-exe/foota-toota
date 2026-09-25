-- External table for Football-Data.org API matches (10 Tier One competitions).
-- Format: JSON Lines. URI: gs://BUCKET/bronze/football_data_org/competition=*/*.jsonl
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_org_matches`
OPTIONS (
    format = 'NEWLINE_DELIMITED_JSON',
    uris = ['gs://BUCKET/bronze/football_data_org/*/*.jsonl'],
    ignore_unknown_values = true
);
