-- Stream dataset: match events that arrive through Pub/Sub, next to the batch
-- layers. Same location as bronze/silver/gold so the views can join across them.
CREATE SCHEMA IF NOT EXISTS `PROJECT.stream`
OPTIONS (
    location    = 'US',
    description = 'Stream: match events and predictions from Pub/Sub'
);
