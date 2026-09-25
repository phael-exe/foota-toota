-- External table for Football-Data.co.uk matches (10 leagues across 3 seasons).
-- Hive partitioned by season and league: gs://BUCKET/bronze/football_data_uk/season=*/league=*/*.csv
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_uk`
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/football_data_uk/*/*/*.csv'],
    skip_leading_rows = 1,
    ignore_unknown_values = true,
    allow_jagged_rows = true,
    max_bad_records = 100
);
