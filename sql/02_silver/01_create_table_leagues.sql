-- Competitions. league_id is lowercased here and everywhere downstream (rule S6).
CREATE OR REPLACE TABLE `PROJECT.silver.leagues` AS
SELECT
    LOWER(`PROJECT.silver.blank_to_null`(id)) AS league_id,
    `PROJECT.silver.blank_to_null`(name) AS league_name,
    `PROJECT.silver.blank_to_null`(sport) AS sport,
    `PROJECT.silver.blank_to_null`(country) AS country,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.leagues`;
