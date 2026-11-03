-- External table for Transfermarkt players directory (50k players).
-- URI: gs://BUCKET/bronze/transfermarkt/players.csv.gz
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_transfermarkt_players`
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/transfermarkt/players.csv.gz'],
    compression = 'GZIP',
    skip_leading_rows = 1,
    ignore_unknown_values = true
);
