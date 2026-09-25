-- Weather observed at kickoff, joined to the match by id.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_matches_weather` (
    match_id               STRING,
    kickoff_utc            STRING,
    venue_name             STRING,
    latitude               STRING,
    longitude              STRING,
    roof                   STRING,
    temperature_c          STRING,
    apparent_temperature_c STRING,
    relative_humidity_pct  STRING,
    precipitation_mm       STRING,
    wind_kph               STRING,
    wind_gust_kph          STRING,
    cloud_cover_pct        STRING,
    condition              STRING
)
OPTIONS (
    format                = 'CSV',
    uris                  = ['gs://BUCKET/matches_weather.csv'],
    skip_leading_rows     = 1,
    field_delimiter       = ',',
    quote                 = '"',
    allow_quoted_newlines = TRUE,
    encoding              = 'UTF-8'
);
