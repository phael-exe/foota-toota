-- Dedicated feature tables for isolated Proof of Concept (PoC) per league.
-- Provides Andre and the Data Science team with ready-to-train feature stores without cross-league noise.

-- 1. Brasileirao Serie A Feature Store
CREATE OR REPLACE TABLE `PROJECT.gold.match_features_brasileirao` AS
SELECT * FROM `PROJECT.gold.match_features`
WHERE league_id = 'brasileirao_serie_a';

-- 2. English Premier League Feature Store
CREATE OR REPLACE TABLE `PROJECT.gold.match_features_epl` AS
SELECT * FROM `PROJECT.gold.match_features`
WHERE league_id = 'epl';
