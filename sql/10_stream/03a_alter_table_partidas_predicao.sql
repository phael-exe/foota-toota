-- The prediction columns for a stream.partidas created before the pipeline called the model
-- API (03_create_table_partidas.sql already has them for a fresh setup). Safe to re-run.
ALTER TABLE `PROJECT.stream.partidas`
    ADD COLUMN IF NOT EXISTS prediction_id STRING,
    ADD COLUMN IF NOT EXISTS model_name STRING,
    ADD COLUMN IF NOT EXISTS model_version STRING,
    ADD COLUMN IF NOT EXISTS prob_home FLOAT64,
    ADD COLUMN IF NOT EXISTS prob_draw FLOAT64,
    ADD COLUMN IF NOT EXISTS prob_away FLOAT64,
    ADD COLUMN IF NOT EXISTS predicted_outcome STRING,
    ADD COLUMN IF NOT EXISTS predicted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS features_ate TIMESTAMP;
