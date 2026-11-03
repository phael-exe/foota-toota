-- Predictions the model API publishes on the `predicoes` topic, written by the Pub/Sub
-- BigQuery subscription `predicoes-bigquery` (use_table_schema: each JSON field lands in the
-- column of the same name, unknown fields are dropped). The topic keeps a message for days
-- only; this table is the history the platform reads. Contract: docs/arquitetura/contratos.md.
-- Partitioned by DATE(predicted_at), clustered by match_id. Created once.
CREATE TABLE IF NOT EXISTS `PROJECT.stream.predicoes` (
    prediction_id     STRING    NOT NULL,
    event_id          STRING,
    match_id          STRING    NOT NULL,
    league_id         STRING,
    model_name        STRING    NOT NULL,
    model_version     STRING    NOT NULL,
    prob_home         FLOAT64,
    prob_draw         FLOAT64,
    prob_away         FLOAT64,
    predicted_outcome STRING    NOT NULL,
    predicted_at      TIMESTAMP NOT NULL
)
PARTITION BY DATE(predicted_at)
CLUSTER BY match_id
OPTIONS (description = 'Histórico de predições publicadas no tópico predicoes');
