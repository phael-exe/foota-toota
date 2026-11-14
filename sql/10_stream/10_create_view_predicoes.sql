-- One row per prediction, in the contract format (docs/arquitetura/contratos.md), read from
-- the events the pipeline enriched in stream.partidas and the daily re-prediction of the coming
-- games in stream.predicoes_lote.
-- A redelivered event repeats its prediction_id; the first one written wins.
-- The proof that a prediction came before the match:
--   live:   prevista_antes_do_jogo  (predicted_at < kickoff_utc)
--   replay: features_antes_do_jogo  (features_ate < kickoff_utc): the replay runs after the
--           fact, so what counts is that the features stop before the kickoff
CREATE OR REPLACE VIEW `PROJECT.gold.predicoes` AS
SELECT
    prediction_id,
    event_id,
    match_id,
    league_id,
    model_name,
    model_version,
    prob_home,
    prob_draw,
    prob_away,
    predicted_outcome,
    predicted_at,
    kickoff_utc,
    mode,
    features_ate,
    predicted_at < kickoff_utc AS prevista_antes_do_jogo,
    features_ate < kickoff_utc AS features_antes_do_jogo
FROM `PROJECT.stream.partidas`
WHERE prediction_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY prediction_id ORDER BY processed_at) = 1

UNION ALL

-- mode 'lote': the daily re-prediction of the coming games (scripts/repredizer.py)
SELECT
    prediction_id,
    CAST(NULL AS STRING) AS event_id,
    match_id,
    league_id,
    model_name,
    model_version,
    prob_home,
    prob_draw,
    prob_away,
    predicted_outcome,
    predicted_at,
    kickoff_utc,
    mode,
    features_ate,
    predicted_at < kickoff_utc AS prevista_antes_do_jogo,
    features_ate < kickoff_utc AS features_antes_do_jogo
FROM `PROJECT.stream.predicoes_lote`;
