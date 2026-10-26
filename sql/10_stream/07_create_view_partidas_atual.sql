-- Current state of each match: the freshest version between batch and the live stream, the
-- view the platform reads for a match page. A Brasileirao fixture streamed under a
-- Football-Data.org id meets its batch row (which may sit under another source's id) through
-- (season, home, away), the key silver uses to dedup that double round robin; other leagues
-- match on match_id. A finished version wins over a newer unfinished one, as in silver.
-- Replay events stay out: they re-enact past rounds for the demo.
CREATE OR REPLACE VIEW `PROJECT.gold.partidas_atual` AS
SELECT * EXCEPT (version_rank)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY
                league_id,
                IF(league_id = 'brasileirao_serie_a',
                   FORMAT('%d|%s|%s', season, home_team_id, away_team_id),
                   match_id)
            ORDER BY status = 'finished' DESC, updated_at DESC, origem = 'stream' DESC
        ) AS version_rank
    FROM `PROJECT.gold.partidas_unificadas`
    WHERE origem = 'batch' OR mode = 'live'
)
WHERE version_rank = 1;
