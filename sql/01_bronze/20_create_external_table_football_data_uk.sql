-- External table for Football-Data.co.uk matches (10 leagues across 3 seasons).
-- Hive partitioned by season and league: gs://BUCKET/bronze/football_data_uk/season=*/league=*/*.csv
-- Every column is declared STRING, like the rest of bronze: autodetect inferred INT64 for HS
-- and the load failed on files where that position holds the referee's name.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_uk` (
    `Div`        STRING,
    `Date`       STRING,
    `Time`       STRING,
    `HomeTeam`   STRING,
    `AwayTeam`   STRING,
    `FTHG`       STRING,
    `FTAG`       STRING,
    `FTR`        STRING,
    `HTHG`       STRING,
    `HTAG`       STRING,
    `HTR`        STRING,
    `Referee`    STRING,
    `HS`         STRING,
    `AS`         STRING,
    `HST`        STRING,
    `AST`        STRING,
    `HF`         STRING,
    `AF`         STRING,
    `HC`         STRING,
    `AC`         STRING,
    `HY`         STRING,
    `AY`         STRING,
    `HR`         STRING,
    `AR`         STRING,
    `B365H`      STRING,
    `B365D`      STRING,
    `B365A`      STRING
)
OPTIONS (
    format = 'CSV',
    uris = ['gs://BUCKET/bronze/football_data_uk/*'],
    skip_leading_rows = 1,
    ignore_unknown_values = true,
    allow_jagged_rows = true,
    max_bad_records = 100
);
