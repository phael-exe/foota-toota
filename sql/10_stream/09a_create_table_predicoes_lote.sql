-- Predictions of the scheduled games of the coming days, made again every day by
-- scripts/repredizer.py with the gold of the previous export (/predict/lote of the model API).
-- The Dataflow predicts a game when the collector sees it change, often weeks ahead; this table
-- keeps the prediction up to date with the odds (out 2 to 4 days before), the Elo and the form.
-- gold.predicoes reads it next to stream.partidas, as mode 'lote'. One row per call, never
-- rewritten: the history shows how a prediction moved as the game came closer.
CREATE TABLE IF NOT EXISTS `PROJECT.stream.predicoes_lote` (
    prediction_id STRING,
    match_id STRING,
    league_id STRING,
    model_name STRING,
    model_version STRING,
    prob_home FLOAT64,
    prob_draw FLOAT64,
    prob_away FLOAT64,
    predicted_outcome STRING,
    predicted_at TIMESTAMP,
    kickoff_utc TIMESTAMP,
    features_ate TIMESTAMP,
    mode STRING
)
PARTITION BY DATE(predicted_at);
