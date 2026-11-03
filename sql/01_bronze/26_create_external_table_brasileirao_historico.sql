-- External table for Brasileirão Série A historical dataset (2003-2026).
-- URI: gs://BUCKET/bronze/brasileirao_historico/*.csv
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_brasileirao_historico`
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/brasileirao_historico/*.csv'],
    skip_leading_rows = 1,
    ignore_unknown_values = true
);
