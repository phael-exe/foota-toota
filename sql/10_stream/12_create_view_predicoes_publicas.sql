-- The predictions the public bucket exports (gold/predictions.parquet): one row per match, under
-- the match_id of silver.matches, which is the id the platform joins on.
-- The stream predicts on Football-Data.org ids (fdorg_*), but silver.matches keeps one row per
-- game across sources and, once a game is over, may keep another source's id (the Brasileirao
-- prefers fduk_BRA_* when the Football-Data.co.uk file holds the result). The game is found
-- again by (league, season, home, away): a domestic league is a double round robin.
-- Per match, the prediction made before the kickoff wins, then a replay whose features stop
-- before it, then the newest. stream_match_id keeps the id the stream used.
CREATE OR REPLACE VIEW `PROJECT.gold.predicoes_publicas` AS
WITH confronto AS (
    SELECT match_id, league_id, season, home_team_id, away_team_id
    FROM `PROJECT.gold.partidas_unificadas`
    WHERE origem = 'stream'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY updated_at DESC) = 1
)
SELECT
    COALESCE(m.match_id, p.match_id) AS match_id,
    p.match_id AS stream_match_id,
    p.* EXCEPT (match_id)
FROM `PROJECT.gold.predicoes` AS p
LEFT JOIN confronto AS c USING (match_id)
LEFT JOIN `PROJECT.silver.matches` AS m
    ON m.league_id = c.league_id
    AND m.season = c.season
    AND m.home_team_id = c.home_team_id
    AND m.away_team_id = c.away_team_id
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY COALESCE(m.match_id, p.match_id)
    ORDER BY
        COALESCE(p.prevista_antes_do_jogo, FALSE) DESC,
        COALESCE(p.features_antes_do_jogo, FALSE) DESC,
        p.predicted_at DESC
) = 1;
