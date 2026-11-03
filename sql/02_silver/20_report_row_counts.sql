-- Consolidated row counts report across all Silver tables.
SELECT 'matches (after deduplication)' AS metric, COUNT(*) AS value FROM `PROJECT.silver.matches`
UNION ALL SELECT 'finished matches',             COUNTIF(status = 'finished')  FROM `PROJECT.silver.matches`
UNION ALL SELECT 'scheduled matches',            COUNTIF(status = 'scheduled') FROM `PROJECT.silver.matches`
UNION ALL SELECT 'team_matches',                 COUNT(*) FROM `PROJECT.silver.team_matches`
UNION ALL SELECT 'teams (global clubs)',         COUNT(*) FROM `PROJECT.silver.teams`
UNION ALL SELECT 'players (global directory)',   COUNT(*) FROM `PROJECT.silver.players`
UNION ALL SELECT 'player_valuations (tm)',       COUNT(*) FROM `PROJECT.silver.player_valuations`
UNION ALL SELECT 'transfers (tm)',               COUNT(*) FROM `PROJECT.silver.transfers`
UNION ALL SELECT 'player_gameweeks (fpl)',       COUNT(*) FROM `PROJECT.silver.player_gameweeks`
UNION ALL SELECT 'news_articles (full text)',    COUNT(*) FROM `PROJECT.silver.news_articles`
UNION ALL SELECT 'standings (official)',         COUNT(*) FROM `PROJECT.silver.standings`
UNION ALL SELECT 'match_stats (shots/cards)',    COUNT(*) FROM `PROJECT.silver.match_stats`
UNION ALL SELECT 'match_odds (betting)',         COUNT(*) FROM `PROJECT.silver.match_odds`
UNION ALL SELECT 'match_tactics (brasileirao)',  COUNT(*) FROM `PROJECT.silver.match_tactics`
UNION ALL SELECT 'h2h (strictly earlier)',       COUNT(*) FROM `PROJECT.silver.h2h`
UNION ALL SELECT 'match_weather',                COUNT(*) FROM `PROJECT.silver.match_weather`
UNION ALL SELECT 'match_goals',                  COUNT(*) FROM `PROJECT.silver.match_goals`
UNION ALL SELECT 'player_match_stats',           COUNT(*) FROM `PROJECT.silver.player_match_stats`;
