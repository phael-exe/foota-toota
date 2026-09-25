-- Per-player, per-match statistics. The metrics themselves stay packed in stats_json.
CREATE OR REPLACE EXTERNAL TABLE `PROJECT.bronze.ext_stored_matches_stats_players` (
    match_id      STRING,
    team_id       STRING,
    team_name     STRING,
    player_id     STRING,
    player_name   STRING,
    position      STRING,
    jersey_number STRING,
    stats_json    STRING
)
OPTIONS (
    format                = 'CSV',
    uris                  = ['gs://BUCKET/stored_matches_stats_players.csv'],
    skip_leading_rows     = 1,
    field_delimiter       = ',',
    quote                 = '"',
    allow_quoted_newlines = TRUE,
    encoding              = 'UTF-8'
);
