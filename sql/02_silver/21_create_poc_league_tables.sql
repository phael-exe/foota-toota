-- Dedicated tables for isolated Proof of Concept (PoC) per league.
-- Allows team members to validate end-to-end models with a single league without cross-league noise.

-- 1. Brasileirao Serie A
CREATE OR REPLACE TABLE `PROJECT.silver.matches_brasileirao`
PARTITION BY DATE(kickoff_utc)
CLUSTER BY home_team_id, away_team_id AS
SELECT * FROM `PROJECT.silver.matches`
WHERE league_id = 'brasileirao_serie_a';

-- 2. English Premier League (EPL)
CREATE OR REPLACE TABLE `PROJECT.silver.matches_epl`
PARTITION BY DATE(kickoff_utc)
CLUSTER BY home_team_id, away_team_id AS
SELECT * FROM `PROJECT.silver.matches`
WHERE league_id = 'epl';
