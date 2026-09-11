-- Player reference data.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_players` (
    id            STRING,
    name          STRING,
    full_name     STRING,
    display_name  STRING,
    position      STRING,
    jersey_number STRING,
    headshot_url  STRING,
    nationality   STRING,
    date_of_birth STRING,
    height        STRING,
    height_cm     STRING,
    weight        STRING,
    weight_kg     STRING,
    team_id       STRING,
    team_name     STRING,
    league_name   STRING,
    sport         STRING
)
OPTIONS (
    format                = 'CSV',
    uris                  = ['gs://BUCKET/players.csv'],
    skip_leading_rows     = 1,
    field_delimiter       = ',',
    quote                 = '"',
    allow_quoted_newlines = TRUE,
    encoding              = 'UTF-8'
);
