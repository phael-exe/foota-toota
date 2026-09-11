-- Clubs. Dropped: abbreviation, flag_url, country, founded_year, stats (100% empty).
-- code is identical to short_name, so it only serves as a fallback.
CREATE OR REPLACE TABLE `PROJECT.silver.teams` AS
SELECT
    `PROJECT.silver.blank_to_null`(id) AS team_id,
    `PROJECT.silver.blank_to_null`(name) AS team_name,
    LOWER(`PROJECT.silver.blank_to_null`(league)) AS league_id,
    `PROJECT.silver.blank_to_null`(sport) AS sport,
    COALESCE(
        `PROJECT.silver.blank_to_null`(short_name),
        `PROJECT.silver.blank_to_null`(code)
    ) AS short_name,
    `PROJECT.silver.blank_to_null`(logo_url) AS logo_url,
    source_file,
    ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.teams`;
