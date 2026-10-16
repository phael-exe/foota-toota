-- Clean match events written by the Dataflow pipeline (streaming/pipeline.py), one row per
-- event: a match shows up once per change (scheduled, in play, finished). Team ids and names
-- are the source's; gold.partidas_unificadas maps them to the silver ids.
-- Partitioned by DATE(published_at): the stream only writes today's partition.
-- Clustered by league_id, match_id: one match reads a few blocks.
-- Created once: a re-run keeps the streamed rows.
CREATE TABLE IF NOT EXISTS `PROJECT.stream.partidas` (
    event_id          STRING    NOT NULL,
    match_id          STRING    NOT NULL,
    league_id         STRING    NOT NULL,
    season            INT64,
    round             STRING,
    kickoff_utc       TIMESTAMP NOT NULL,
    status            STRING    NOT NULL,
    home_team_id      STRING    NOT NULL,
    home_team_name    STRING,
    away_team_id      STRING    NOT NULL,
    away_team_name    STRING,
    score_home        INT64,
    score_away        INT64,
    outcome           STRING,
    mode              STRING    NOT NULL,
    source_id         STRING    NOT NULL,
    source_updated_at TIMESTAMP,
    published_at      TIMESTAMP NOT NULL,
    processed_at      TIMESTAMP NOT NULL
)
PARTITION BY DATE(published_at)
CLUSTER BY league_id, match_id
OPTIONS (description = 'Silver do stream: eventos de partida validados pelo Dataflow');
