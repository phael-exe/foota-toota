-- Weather at kickoff (4,450 rows). One exact duplicate, removed by DISTINCT.
-- wind_kph, wind_gust_kph and cloud_cover_pct are 100% empty; roof is constant.
-- C1: this is OBSERVED weather, not a forecast, so it may only be used for retrospective
--     analysis. It must never become a model feature.
CREATE OR REPLACE TABLE `PROJECT.silver.match_weather` AS
SELECT DISTINCT
    `PROJECT.silver.blank_to_null`(match_id) AS match_id,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(kickoff_utc) AS TIMESTAMP) AS kickoff_utc,
    `PROJECT.silver.blank_to_null`(venue_name) AS venue_name,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(latitude)  AS FLOAT64) AS latitude,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(longitude) AS FLOAT64) AS longitude,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(temperature_c) AS FLOAT64) AS temperature_c,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(apparent_temperature_c) AS FLOAT64) AS apparent_temperature_c,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(relative_humidity_pct) AS FLOAT64) AS relative_humidity_pct,
    SAFE_CAST(`PROJECT.silver.blank_to_null`(precipitation_mm) AS FLOAT64) AS precipitation_mm,
    `PROJECT.silver.blank_to_null`(condition) AS condition
FROM `PROJECT.bronze.matches_weather`;
