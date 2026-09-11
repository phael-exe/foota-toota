-- Gold dataset: one row per match, model features and model artifacts.
CREATE SCHEMA IF NOT EXISTS `PROJECT.gold`
OPTIONS (
    location    = 'US',
    description = 'Gold: features per match'
);
