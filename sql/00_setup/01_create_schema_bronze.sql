-- Bronze dataset: raw CSVs landed from GCS, every column typed as STRING.
CREATE SCHEMA IF NOT EXISTS `PROJECT.bronze`
OPTIONS (
    location    = 'US',
    description = 'Bronze: CSVs from GCS, STRING columns'
);
