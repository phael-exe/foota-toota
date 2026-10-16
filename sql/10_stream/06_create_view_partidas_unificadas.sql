-- Batch and stream side by side (Trabalho 2): every silver match (origem = 'batch') stacked on
-- the latest state of each streamed match (origem = 'stream'). Stream clubs go through
-- silver.team_alias like silver's own Football-Data.org rows, so a Brasileirao fixture carries
-- the same team ids in both halves. Demo: the stream half grows while the batch stays put.
--   SELECT origem, mode, COUNT(*) FROM gold.partidas_unificadas GROUP BY 1, 2
-- A finished version beats any later one: the source API sometimes answers from a stale cache
-- for a few minutes and sends a played round back as scheduled.
CREATE OR REPLACE VIEW `PROJECT.gold.partidas_unificadas` AS
WITH stream_latest AS (
    SELECT *
    FROM `PROJECT.stream.partidas`
    WHERE TRUE
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY match_id, mode
        ORDER BY status = 'finished' DESC, published_at DESC
    ) = 1
)
SELECT
    'batch'              AS origem,
    CAST(NULL AS STRING) AS mode,
    match_id,
    league_id,
    season,
    round,
    kickoff_utc,
    status,
    home_team_id,
    away_team_id,
    home_team_name,
    away_team_name,
    score_home,
    score_away,
    outcome,
    source_id,
    ingested_at          AS updated_at
FROM `PROJECT.silver.matches`
UNION ALL
SELECT
    'stream',
    s.mode,
    s.match_id,
    s.league_id,
    s.season,
    s.round,
    s.kickoff_utc,
    s.status,
    COALESCE(ah.team_id, s.home_team_id),
    COALESCE(aa.team_id, s.away_team_id),
    COALESCE(ah.team_id, s.home_team_name),
    COALESCE(aa.team_id, s.away_team_name),
    s.score_home,
    s.score_away,
    s.outcome,
    s.source_id,
    s.published_at
FROM stream_latest s
LEFT JOIN `PROJECT.silver.team_alias` ah
       ON ah.league_id = s.league_id AND ah.source_id = s.source_id
      AND ah.raw_name = s.home_team_name
LEFT JOIN `PROJECT.silver.team_alias` aa
       ON aa.league_id = s.league_id AND aa.source_id = s.source_id
      AND aa.raw_name = s.away_team_name;
