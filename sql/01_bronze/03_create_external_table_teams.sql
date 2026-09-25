-- Club reference data as delivered by the API export.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_teams` (
    code         STRING,
    id           STRING,
    name         STRING,
    short_name   STRING,
    abbreviation STRING,
    logo_url     STRING,
    flag_url     STRING,
    sport        STRING,
    league       STRING,
    country      STRING,
    founded_year STRING,
    stats        STRING
)
OPTIONS (
    format                = 'CSV',
    uris                  = ['gs://BUCKET/teams.csv'],
    skip_leading_rows     = 1,
    field_delimiter       = ',',
    quote                 = '"',
    allow_quoted_newlines = TRUE,
    encoding              = 'UTF-8'
);
