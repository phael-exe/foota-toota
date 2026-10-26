-- External table for Transfermarkt transfers history (175k transfers).
-- URI: gs://BUCKET/bronze/transfermarkt/transfers.csv.gz
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_transfermarkt_transfers`
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/transfermarkt/transfers.csv.gz'],
    compression = 'GZIP',
    skip_leading_rows = 1,
    ignore_unknown_values = true
);
