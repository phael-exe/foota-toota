-- Clubs dimension: one row per canonical team_id of silver.team_map, the id silver.matches,
-- silver.standings and the gold use for a club. Carries the club's id or name in each source,
-- so a consumer can reach the club from any of them, plus short name, three-letter code and
-- crest from Football-Data.org (Big Balls for the EPL clubs it lacks). league_id is the league
-- of the club's newest game; country follows from that league.
CREATE OR REPLACE TABLE `PROJECT.silver.teams` AS
WITH clubs AS (
    SELECT
        team_id,
        ANY_VALUE(team_name) AS team_name,
        COALESCE(
            ANY_VALUE(IF(league_id = 'champions_league', NULL, league_id) HAVING MAX last_match_date),
            MAX(IF(league_id = 'champions_league', NULL, league_id)),
            ANY_VALUE(league_id)
        ) AS league_id,
        ARRAY_AGG(short_name IGNORE NULLS ORDER BY source_id = 'football_data_org' DESC LIMIT 1)[SAFE_OFFSET(0)] AS short_name,
        ARRAY_AGG(tla IGNORE NULLS ORDER BY source_id = 'football_data_org' DESC LIMIT 1)[SAFE_OFFSET(0)] AS tla,
        ARRAY_AGG(crest_url IGNORE NULLS ORDER BY source_id = 'football_data_org' DESC LIMIT 1)[SAFE_OFFSET(0)] AS crest_url,
        STRING_AGG(DISTINCT IF(source_id = 'bigballs', raw_team_id, NULL), '|') AS bigballs_id,
        STRING_AGG(DISTINCT IF(source_id = 'football_data_org', raw_team_id, NULL), '|') AS football_data_org_id,
        STRING_AGG(DISTINCT IF(source_id IN ('football_data_uk', 'football_data_uk_bra'), raw_team_id, NULL), '|') AS football_data_uk_name,
        STRING_AGG(DISTINCT IF(source_id = 'brasileirao_historico', raw_team_id, NULL), '|') AS brasileirao_historico_name,
        MAX(last_match_date) AS last_match_date
    FROM `PROJECT.silver.team_map`
    GROUP BY team_id
)
SELECT
    team_id,
    team_name,
    COALESCE(short_name, team_name) AS short_name,
    tla,
    league_id,
    CASE league_id
        WHEN 'epl'                  THEN 'England'
        WHEN 'championship'         THEN 'England'
        WHEN 'la_liga'              THEN 'Spain'
        WHEN 'serie_a'              THEN 'Italy'
        WHEN 'bundesliga'           THEN 'Germany'
        WHEN 'ligue_1'              THEN 'France'
        WHEN 'eredivisie'           THEN 'Netherlands'
        WHEN 'primeira_liga'        THEN 'Portugal'
        WHEN 'belgian_pro_league'   THEN 'Belgium'
        WHEN 'scottish_premiership' THEN 'Scotland'
        WHEN 'brasileirao_serie_a'  THEN 'Brazil'
    END AS country,
    crest_url,
    bigballs_id,
    football_data_org_id,
    football_data_uk_name,
    brasileirao_historico_name,
    last_match_date,
    CURRENT_TIMESTAMP() AS transformed_at
FROM clubs;
