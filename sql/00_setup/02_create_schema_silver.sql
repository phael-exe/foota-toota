-- Silver dataset: typed, deduplicated and normalized tables.
CREATE SCHEMA IF NOT EXISTS `PROJECT.silver`
OPTIONS (
    location    = 'US',
    description = 'Silver: typed, deduplicated, normalized'
);
