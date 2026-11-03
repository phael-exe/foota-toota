-- Raw landing of every message on the `eventos` topic, written by the Pub/Sub BigQuery
-- subscription `eventos-bigquery` with no code of ours: the stream's bronze. It keeps landing
-- while the Dataflow job is off, so no event is lost. The columns are the ones Pub/Sub writes
-- with write_metadata on and the table schema off.
-- Partitioned by DATE(publish_time). Created once: a re-run keeps what already landed.
CREATE TABLE IF NOT EXISTS `PROJECT.stream.eventos_brutos` (
    subscription_name STRING,
    message_id        STRING,
    publish_time      TIMESTAMP,
    data              STRING,
    attributes        STRING
)
PARTITION BY DATE(publish_time)
OPTIONS (description = 'Bronze do stream: mensagens do tópico eventos como chegaram');
