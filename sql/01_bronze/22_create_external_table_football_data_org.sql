-- External table for Football-Data.org API matches (10 Tier One competitions).
-- Format: JSON Lines. URI: gs://BUCKET/bronze/football_data_org/competition=*/*.jsonl
-- Nested objects (teams, score, season...) stay JSON, which silver reads with JSON_VALUE;
-- autodetect would turn them into STRUCTs and the dates into TIMESTAMPs.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_football_data_org_matches` (
    `id`                INT64,
    `utcDate`           STRING,
    `status`            STRING,
    `matchday`          INT64,
    `stage`             STRING,
    `group`             STRING,
    `lastUpdated`       STRING,
    `homeTeam`          JSON,
    `awayTeam`          JSON,
    `score`             JSON,
    `odds`              JSON,
    `referees`          JSON,
    `competition`       JSON,
    `season`            JSON,
    `_competition_code` STRING,
    `_competition_name` STRING
)
OPTIONS (
    format = 'NEWLINE_DELIMITED_JSON',
    uris = ['gs://BUCKET/bronze/football_data_org/*'],
    ignore_unknown_values = true
);
