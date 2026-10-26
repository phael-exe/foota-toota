-- External table for Transfermarkt clubs directory (796 clubs).
-- URI: gs://BUCKET/bronze/transfermarkt/clubs.csv.gz
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_transfermarkt_clubs`
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/transfermarkt/clubs.csv.gz'],
    compression = 'GZIP',
    skip_leading_rows = 1,
    ignore_unknown_values = true
);
