-- Competitions and Leagues dimension.
-- Integrates all covered leagues across BBD, Football-Data.co.uk, Brasileirao and Football-Data.org.
-- S6: league_id is normalized to lower case.
CREATE OR REPLACE TABLE `PROJECT.silver.leagues` AS
WITH base_competitions AS (
    SELECT 'epl' AS league_id, 'Premier League' AS league_name, 'football' AS sport, 'England' AS country, 'ENG' AS country_code, 'UEFA' AS confederation, 1 AS tier
    UNION ALL SELECT 'championship', 'EFL Championship', 'football', 'England', 'ENG', 'UEFA', 2
    UNION ALL SELECT 'brasileirao_serie_a', 'Campeonato Brasileiro Série A', 'football', 'Brazil', 'BRA', 'CONMEBOL', 1
    UNION ALL SELECT 'la_liga', 'La Liga', 'football', 'Spain', 'ESP', 'UEFA', 1
    UNION ALL SELECT 'serie_a', 'Serie A', 'football', 'Italy', 'ITA', 'UEFA', 1
    UNION ALL SELECT 'bundesliga', 'Bundesliga', 'football', 'Germany', 'GER', 'UEFA', 1
    UNION ALL SELECT 'ligue_1', 'Ligue 1', 'football', 'France', 'FRA', 'UEFA', 1
    UNION ALL SELECT 'eredivisie', 'Eredivisie', 'football', 'Netherlands', 'NED', 'UEFA', 1
    UNION ALL SELECT 'primeira_liga', 'Primeira Liga', 'football', 'Portugal', 'POR', 'UEFA', 1
    UNION ALL SELECT 'belgian_pro_league', 'Belgian Pro League', 'football', 'Belgium', 'BEL', 'UEFA', 1
    UNION ALL SELECT 'scottish_premiership', 'Scottish Premiership', 'football', 'Scotland', 'SCO', 'UEFA', 1
    UNION ALL SELECT 'champions_league', 'UEFA Champions League', 'football', 'Europe', 'EUR', 'UEFA', 1
),
from_bronze AS (
    SELECT
        LOWER(`PROJECT.silver.blank_to_null`(id)) AS league_id,
        `PROJECT.silver.blank_to_null`(name) AS league_name,
        `PROJECT.silver.blank_to_null`(sport) AS sport,
        `PROJECT.silver.blank_to_null`(country) AS country,
        source_file,
        ingested_at
    FROM `PROJECT.bronze.leagues`
)
SELECT
    COALESCE(b.league_id, z.league_id) AS league_id,
    COALESCE(z.league_name, b.league_name) AS league_name,
    COALESCE(b.sport, z.sport, 'football') AS sport,
    COALESCE(b.country, z.country) AS country,
    z.country_code,
    z.confederation,
    z.tier,
    COALESCE(b.source_file, 'seed') AS source_file,
    COALESCE(b.ingested_at, CURRENT_TIMESTAMP()) AS ingested_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM base_competitions z
FULL OUTER JOIN from_bronze b ON z.league_id = b.league_id;

-- Create view synonym for canonical dictionary alignment
CREATE OR REPLACE VIEW `PROJECT.silver.competitions` AS
SELECT * FROM `PROJECT.silver.leagues`;
