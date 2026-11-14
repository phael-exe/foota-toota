-- External table for the odds of the upcoming games (Football-Data.co.uk fixtures.csv and
-- new_league_fixtures.csv, normalized by scripts/fetch_bronze.py into one column order, the
-- Brasileirao as Div BRA). The site only lists the coming days, so every collection is kept as a
-- daily snapshot. The schema is explicit: autodetect retyped columns of other sources before.
-- URI: gs://BUCKET/bronze/football_data_uk_fixtures/dt=YYYY-MM-DD/fixtures.csv
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_uk_fixtures` (
    Div STRING,
    Date STRING,
    Time STRING,
    HomeTeam STRING,
    AwayTeam STRING,
    PSH STRING,
    PSD STRING,
    PSA STRING,
    AvgH STRING,
    AvgD STRING,
    AvgA STRING,
    B365H STRING,
    B365D STRING,
    B365A STRING
)
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/football_data_uk_fixtures/*'],
    skip_leading_rows = 1
);
