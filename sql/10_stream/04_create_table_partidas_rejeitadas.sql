-- Events the pipeline refused, with the reason and the raw payload: a broken producer shows
-- up here instead of vanishing. Rows BigQuery itself rejects land here too.
-- Partitioned by DATE(processed_at). Created once.
CREATE TABLE IF NOT EXISTS `PROJECT.stream.partidas_rejeitadas` (
    event_id     STRING,
    reason       STRING    NOT NULL,
    payload      STRING,
    processed_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(processed_at)
OPTIONS (description = 'Quarentena do stream: eventos recusados e o motivo');
