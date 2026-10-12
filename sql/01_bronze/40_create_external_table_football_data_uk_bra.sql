-- External table for the Football-Data.co.uk Brazil Serie A file (2012 onwards, one file,
-- explicit Season column, closing odds from Pinnacle, Bet365 and the market average).
-- URI: gs://BUCKET/bronze/football_data_uk_bra/BRA.csv
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_uk_bra`
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/football_data_uk_bra/*.csv'],
    skip_leading_rows = 1,
    ignore_unknown_values = true,
    allow_jagged_rows = true
);
