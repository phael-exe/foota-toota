-- External table for the Premier League files of Football-Data.co.uk before 2022/23 (2014/15 to
-- 2021/22), kept apart from bronze.football_data_uk: silver.match_odds is the only reader. Big Balls
-- already holds these games in silver.matches, and the odds give the model's training the market.
-- Same columns as bronze.football_data_uk (scripts/fetch_bronze.py writes both).
-- URI: gs://BUCKET/bronze/football_data_uk_epl_historico/season=*/matches.csv
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_uk_epl_historico` (
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
    uris = ['gs://BUCKET/bronze/football_data_uk_epl_historico/*'],
    skip_leading_rows = 1,
    ignore_unknown_values = true,
    allow_jagged_rows = true,
    max_bad_records = 100
);
