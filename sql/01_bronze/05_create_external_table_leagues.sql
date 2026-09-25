-- Competition reference data.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_leagues` (
    id      STRING,
    name    STRING,
    sport   STRING,
    country STRING
)
OPTIONS (
    format                = 'CSV',
    uris                  = ['gs://BUCKET/leagues.csv'],
    skip_leading_rows     = 1,
    field_delimiter       = ',',
    quote                 = '"',
    allow_quoted_newlines = TRUE,
    encoding              = 'UTF-8'
);
