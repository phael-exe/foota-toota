-- External table for Transfermarkt player valuations history (656k valuations).
-- URI: gs://BUCKET/bronze/transfermarkt/player_valuations.csv.gz
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_transfermarkt_player_valuations`
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/transfermarkt/player_valuations.csv.gz'],
    compression = 'GZIP',
    skip_leading_rows = 1,
    ignore_unknown_values = true
);
