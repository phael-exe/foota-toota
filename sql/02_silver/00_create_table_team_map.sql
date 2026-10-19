-- Club identity across sources: one row per club id a source uses (source_id, raw_team_id) and
-- the canonical team_id silver gives that club, so past games, fixtures and standings of a club
-- share one id. Canonical ids, by league family:
--   EPL clubs          the Big Balls UUID (the PoC history and gold.match_features_epl use it)
--   Brasileirao clubs  the Brasileirao Historico name, through silver.team_alias
--   other clubs        the Football-Data.org id; a club only in old Football-Data.co.uk seasons
--                      keeps its Football-Data.co.uk name
-- Links are learned from the games themselves: two sources holding the same league, date and
-- (when both are played) score hold the same game, so its home clubs are one club and so are
-- its away clubs. A link needs the two clubs to be each other's best match, three votes or more,
-- and at least twice the votes of the runner-up (by date alone, a full weekend gives too many
-- candidates: Football-Data.org reaches Big Balls through Football-Data.co.uk, whose scores
-- settle it). `unresolved` flags a club whose games overlap another source's coverage but whose
-- team_id that source never uses: assert S22 stops the pipeline on it, because that club would
-- show twice in silver.matches.
CREATE OR REPLACE TABLE `PROJECT.silver.team_map` AS
WITH appearances AS (
    SELECT DISTINCT
        'bigballs' AS source_id,
        'epl' AS league_id,
        DATE(SAFE_CAST(`PROJECT.silver.blank_to_null`(kickoff_utc) AS TIMESTAMP)) AS match_date,
        `PROJECT.silver.blank_to_null`(home_id) AS home_id,
        `PROJECT.silver.blank_to_null`(away_id) AS away_id,
        `PROJECT.silver.blank_to_null`(home_name) AS home_name,
        `PROJECT.silver.blank_to_null`(away_name) AS away_name,
        IF(LOWER(status) = 'finished', SAFE_CAST(score_home AS INT64), NULL) AS score_home,
        IF(LOWER(status) = 'finished', SAFE_CAST(score_away AS INT64), NULL) AS score_away
    FROM `PROJECT.bronze.stored_matches`
    WHERE LOWER(league) = 'epl'

    UNION ALL

    SELECT DISTINCT
        'football_data_uk',
        CASE Div
            WHEN 'E0'  THEN 'epl'
            WHEN 'E1'  THEN 'championship'
            WHEN 'SP1' THEN 'la_liga'
            WHEN 'I1'  THEN 'serie_a'
            WHEN 'D1'  THEN 'bundesliga'
            WHEN 'F1'  THEN 'ligue_1'
            WHEN 'N1'  THEN 'eredivisie'
            WHEN 'P1'  THEN 'primeira_liga'
            WHEN 'B1'  THEN 'belgian_pro_league'
            WHEN 'SC0' THEN 'scottish_premiership'
            ELSE LOWER(Div)
        END,
        COALESCE(SAFE.PARSE_DATE('%d/%m/%Y', Date), SAFE.PARSE_DATE('%d/%m/%y', Date)),
        HomeTeam,
        AwayTeam,
        HomeTeam,
        AwayTeam,
        SAFE_CAST(FTHG AS INT64),
        SAFE_CAST(FTAG AS INT64)
    FROM `PROJECT.bronze.football_data_uk`
    WHERE HomeTeam IS NOT NULL AND AwayTeam IS NOT NULL

    UNION ALL

    SELECT DISTINCT
        'football_data_org',
        CASE _competition_code
            WHEN 'PL'  THEN 'epl'
            WHEN 'BSA' THEN 'brasileirao_serie_a'
            WHEN 'PD'  THEN 'la_liga'
            WHEN 'BL1' THEN 'bundesliga'
            WHEN 'SA'  THEN 'serie_a'
            WHEN 'FL1' THEN 'ligue_1'
            WHEN 'CL'  THEN 'champions_league'
            WHEN 'ELC' THEN 'championship'
            WHEN 'DED' THEN 'eredivisie'
            WHEN 'PPL' THEN 'primeira_liga'
            ELSE LOWER(_competition_code)
        END,
        DATE(SAFE_CAST(utcDate AS TIMESTAMP)),
        CAST(JSON_VALUE(homeTeam, '$.id') AS STRING),
        CAST(JSON_VALUE(awayTeam, '$.id') AS STRING),
        JSON_VALUE(homeTeam, '$.name'),
        JSON_VALUE(awayTeam, '$.name'),
        IF(LOWER(status) = 'finished', SAFE_CAST(JSON_VALUE(score, '$.fullTime.home') AS INT64), NULL),
        IF(LOWER(status) = 'finished', SAFE_CAST(JSON_VALUE(score, '$.fullTime.away') AS INT64), NULL)
    FROM `PROJECT.bronze.football_data_org_matches`
    WHERE JSON_VALUE(homeTeam, '$.id') IS NOT NULL AND JSON_VALUE(awayTeam, '$.id') IS NOT NULL
),

-- The games that can link clubs: the Champions League has a single source, and the
-- Brasileirao goes through the hand-made silver.team_alias
fixtures AS (
    SELECT *
    FROM appearances
    WHERE league_id NOT IN ('champions_league', 'brasileirao_serie_a')
),

pairs AS (
    SELECT
        a.source_id AS source_a,
        b.source_id AS source_b,
        a.home_id AS home_a,
        a.away_id AS away_a,
        b.home_id AS home_b,
        b.away_id AS away_b
    FROM fixtures a
    JOIN fixtures b
      ON b.league_id = a.league_id
     AND b.match_date = a.match_date
     AND ((a.source_id = 'football_data_uk' AND b.source_id IN ('football_data_org', 'bigballs'))
          OR (a.source_id = 'football_data_org' AND b.source_id = 'bigballs'))
     -- two results of the same game agree; a game not yet played only shares the date
     AND (a.score_home IS NULL OR b.score_home IS NULL
          OR (a.score_home = b.score_home AND a.score_away = b.score_away))
),

vote_counts AS (
    SELECT source_a, raw_a, source_b, raw_b, COUNT(*) AS votes
    FROM (
        SELECT source_a, home_a AS raw_a, source_b, home_b AS raw_b FROM pairs
        UNION ALL
        SELECT source_a, away_a, source_b, away_b FROM pairs
    )
    GROUP BY source_a, raw_a, source_b, raw_b
),

ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY source_a, raw_a, source_b ORDER BY votes DESC) AS rank_a,
        ROW_NUMBER() OVER (PARTITION BY source_b, raw_b, source_a ORDER BY votes DESC) AS rank_b,
        NTH_VALUE(votes, 2) OVER (
            PARTITION BY source_a, raw_a, source_b ORDER BY votes DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS runner_up_a,
        NTH_VALUE(votes, 2) OVER (
            PARTITION BY source_b, raw_b, source_a ORDER BY votes DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS runner_up_b
    FROM vote_counts
),

links AS (
    SELECT source_a, raw_a, source_b, raw_b, votes
    FROM ranked
    WHERE rank_a = 1 AND rank_b = 1
      AND votes >= 3
      AND votes >= 2 * COALESCE(runner_up_a, 0)
      AND votes >= 2 * COALESCE(runner_up_b, 0)
),

-- Every club id a source uses, with its newest name, league and Football-Data.org details
clubs AS (
    SELECT
        source_id,
        raw_team_id,
        ANY_VALUE(raw_team_name HAVING MAX match_date) AS raw_team_name,
        -- the domestic league of the newest game; a Champions League game says nothing about it
        ANY_VALUE(IF(league_id = 'champions_league', NULL, league_id) HAVING MAX match_date) AS newest_league,
        MAX(IF(league_id = 'champions_league', NULL, league_id)) AS any_domestic_league,
        MAX(match_date) AS last_match_date
    FROM (
        SELECT source_id, league_id, match_date, home_id AS raw_team_id, home_name AS raw_team_name FROM appearances
        UNION ALL
        SELECT source_id, league_id, match_date, away_id, away_name FROM appearances
    )
    WHERE raw_team_id IS NOT NULL
    GROUP BY source_id, raw_team_id
),

fdorg_details AS (
    SELECT
        id AS raw_team_id,
        ANY_VALUE(short_name HAVING MAX utc_date) AS short_name,
        ANY_VALUE(tla HAVING MAX utc_date) AS tla,
        ANY_VALUE(crest HAVING MAX utc_date) AS crest_url
    FROM (
        SELECT CAST(JSON_VALUE(homeTeam, '$.id') AS STRING) AS id, JSON_VALUE(homeTeam, '$.shortName') AS short_name,
               JSON_VALUE(homeTeam, '$.tla') AS tla, JSON_VALUE(homeTeam, '$.crest') AS crest, utcDate AS utc_date
        FROM `PROJECT.bronze.football_data_org_matches`
        UNION ALL
        SELECT CAST(JSON_VALUE(awayTeam, '$.id') AS STRING), JSON_VALUE(awayTeam, '$.shortName'),
               JSON_VALUE(awayTeam, '$.tla'), JSON_VALUE(awayTeam, '$.crest'), utcDate
        FROM `PROJECT.bronze.football_data_org_matches`
    )
    WHERE id IS NOT NULL
    GROUP BY id
),

bigballs_details AS (
    SELECT
        `PROJECT.silver.blank_to_null`(id) AS raw_team_id,
        ANY_VALUE(`PROJECT.silver.blank_to_null`(short_name)) AS short_name,
        ANY_VALUE(`PROJECT.silver.blank_to_null`(abbreviation)) AS tla,
        ANY_VALUE(`PROJECT.silver.blank_to_null`(logo_url)) AS crest_url
    FROM `PROJECT.bronze.teams`
    GROUP BY 1
),

fdorg_to_bigballs AS (
    SELECT raw_a AS fdorg_id, raw_b AS bigballs_id, votes
    FROM links WHERE source_a = 'football_data_org' AND source_b = 'bigballs'
),
fduk_to_bigballs AS (
    SELECT raw_a AS fduk_name, raw_b AS bigballs_id, votes
    FROM links WHERE source_a = 'football_data_uk' AND source_b = 'bigballs'
),
fduk_to_fdorg AS (
    SELECT raw_a AS fduk_name, raw_b AS fdorg_id, votes
    FROM links WHERE source_a = 'football_data_uk' AND source_b = 'football_data_org'
),

-- A club relegated from the EPL meets Big Balls only through its Football-Data.co.uk name
fdorg_to_bigballs_via_fduk AS (
    SELECT f.fdorg_id, ANY_VALUE(b.bigballs_id) AS bigballs_id
    FROM fduk_to_fdorg f
    JOIN fduk_to_bigballs b USING (fduk_name)
    GROUP BY f.fdorg_id
),

bigballs_names AS (
    SELECT raw_team_id, raw_team_name FROM clubs WHERE source_id = 'bigballs'
),

fdorg_canonical AS (
    SELECT
        c.raw_team_id,
        c.raw_team_name,
        COALESCE(c.newest_league, c.any_domestic_league, 'champions_league') AS league_id,
        c.last_match_date,
        CASE
            WHEN d.bigballs_id IS NOT NULL THEN d.bigballs_id
            WHEN v.bigballs_id IS NOT NULL THEN v.bigballs_id
            WHEN al.team_id IS NOT NULL THEN al.team_id
            ELSE c.raw_team_id
        END AS team_id,
        CASE
            WHEN d.bigballs_id IS NOT NULL THEN bd.raw_team_name
            WHEN v.bigballs_id IS NOT NULL THEN bv.raw_team_name
            WHEN al.team_id IS NOT NULL THEN al.team_id
            ELSE c.raw_team_name
        END AS team_name,
        CASE
            WHEN d.bigballs_id IS NOT NULL THEN 'fixtures_bigballs'
            WHEN v.bigballs_id IS NOT NULL THEN 'fixtures_bigballs_via_fduk'
            WHEN al.team_id IS NOT NULL THEN 'team_alias'
            ELSE 'source'
        END AS method,
        d.votes
    FROM clubs c
    LEFT JOIN fdorg_to_bigballs d ON d.fdorg_id = c.raw_team_id
    LEFT JOIN fdorg_to_bigballs_via_fduk v ON v.fdorg_id = c.raw_team_id
    LEFT JOIN bigballs_names bd ON bd.raw_team_id = d.bigballs_id
    LEFT JOIN bigballs_names bv ON bv.raw_team_id = v.bigballs_id
    -- same rule as silver.matches: a Brasileirao club named in the alias takes its historico id
    LEFT JOIN `PROJECT.silver.team_alias` al
           ON al.league_id = 'brasileirao_serie_a' AND al.source_id = 'football_data_org'
          AND al.raw_name = c.raw_team_name
          AND c.any_domestic_league = 'brasileirao_serie_a'
    WHERE c.source_id = 'football_data_org'
),

fduk_canonical AS (
    SELECT
        c.raw_team_id,
        c.raw_team_name,
        COALESCE(c.newest_league, c.any_domestic_league) AS league_id,
        c.last_match_date,
        CASE
            WHEN b.bigballs_id IS NOT NULL THEN b.bigballs_id
            WHEN o.fdorg_id IS NOT NULL THEN fo.team_id
            ELSE c.raw_team_id
        END AS team_id,
        CASE
            WHEN b.bigballs_id IS NOT NULL THEN bn.raw_team_name
            WHEN o.fdorg_id IS NOT NULL THEN fo.team_name
            ELSE c.raw_team_name
        END AS team_name,
        CASE
            WHEN b.bigballs_id IS NOT NULL THEN 'fixtures_bigballs'
            WHEN o.fdorg_id IS NOT NULL THEN 'fixtures_football_data_org'
            ELSE 'source'
        END AS method,
        COALESCE(b.votes, o.votes) AS votes
    FROM clubs c
    LEFT JOIN fduk_to_bigballs b ON b.fduk_name = c.raw_team_id
    LEFT JOIN bigballs_names bn ON bn.raw_team_id = b.bigballs_id
    LEFT JOIN fduk_to_fdorg o ON o.fduk_name = c.raw_team_id
    LEFT JOIN fdorg_canonical fo ON fo.raw_team_id = o.fdorg_id
    WHERE c.source_id = 'football_data_uk'
),

mapped AS (
    SELECT
        'bigballs' AS source_id, c.raw_team_id, c.raw_team_name, 'epl' AS league_id, c.last_match_date,
        c.raw_team_id AS team_id, c.raw_team_name AS team_name, 'source' AS method,
        CAST(NULL AS INT64) AS votes
    FROM clubs c
    WHERE c.source_id = 'bigballs'
    UNION ALL
    SELECT 'football_data_org', raw_team_id, raw_team_name, league_id, last_match_date,
           team_id, team_name, method, votes
    FROM fdorg_canonical
    UNION ALL
    SELECT 'football_data_uk', raw_team_id, raw_team_name, league_id, last_match_date,
           team_id, team_name, method, votes
    FROM fduk_canonical
    UNION ALL
    -- Brasileirao: the historico name is the id; the Brazil file of Football-Data.co.uk goes
    -- through silver.team_alias like in silver.matches
    SELECT DISTINCT 'brasileirao_historico', name, name, 'brasileirao_serie_a', CAST(NULL AS DATE),
           name, name, 'source', CAST(NULL AS INT64)
    FROM (
        SELECT mandante AS name FROM `PROJECT.bronze.brasileirao_historico`
        UNION ALL
        SELECT visitante FROM `PROJECT.bronze.brasileirao_historico`
    )
    WHERE name IS NOT NULL
    UNION ALL
    SELECT 'football_data_uk_bra', b.name, b.name, 'brasileirao_serie_a', MAX(b.match_date),
           COALESCE(ANY_VALUE(a.team_id), b.name), COALESCE(ANY_VALUE(a.team_id), b.name),
           IF(ANY_VALUE(a.team_id) IS NULL, 'source', 'team_alias'), CAST(NULL AS INT64)
    FROM (
        SELECT Home AS name, Date AS match_date FROM `PROJECT.bronze.football_data_uk_bra`
        UNION ALL
        SELECT Away, Date FROM `PROJECT.bronze.football_data_uk_bra`
    ) b
    LEFT JOIN `PROJECT.silver.team_alias` a
           ON a.league_id = 'brasileirao_serie_a' AND a.source_id = 'football_data_uk'
          AND a.raw_name = b.name
    WHERE b.name IS NOT NULL
    GROUP BY b.name
),

-- Clubs whose games share league and date with another source's games must reach, directly or
-- through a third source, a club of that source under the same team_id
overlaps AS (
    SELECT DISTINCT c.source_id, c.raw_team_id, o.source_id AS other_source
    FROM (
        SELECT source_id, league_id, match_date, home_id AS raw_team_id FROM fixtures
        UNION ALL
        SELECT source_id, league_id, match_date, away_id FROM fixtures
    ) c
    JOIN (SELECT DISTINCT source_id, league_id, match_date FROM fixtures) o
      ON o.league_id = c.league_id AND o.match_date = c.match_date AND o.source_id != c.source_id
),

unresolved AS (
    SELECT DISTINCT o.source_id, o.raw_team_id
    FROM overlaps o
    JOIN mapped m USING (source_id, raw_team_id)
    LEFT JOIN (SELECT DISTINCT source_id, team_id FROM mapped) x
           ON x.source_id = o.other_source AND x.team_id = m.team_id
    WHERE x.team_id IS NULL
)

SELECT
    m.source_id,
    m.raw_team_id,
    m.raw_team_name,
    m.league_id,
    m.team_id,
    m.team_name,
    m.method,
    m.votes,
    COALESCE(fd.short_name, bb.short_name) AS short_name,
    COALESCE(fd.tla, bb.tla) AS tla,
    COALESCE(fd.crest_url, bb.crest_url) AS crest_url,
    m.last_match_date,
    u.raw_team_id IS NOT NULL AS unresolved,
    CURRENT_TIMESTAMP() AS transformed_at
FROM mapped m
LEFT JOIN fdorg_details fd ON m.source_id = 'football_data_org' AND fd.raw_team_id = m.raw_team_id
LEFT JOIN bigballs_details bb ON m.source_id = 'bigballs' AND bb.raw_team_id = m.raw_team_id
LEFT JOIN unresolved u ON u.source_id = m.source_id AND u.raw_team_id = m.raw_team_id;
