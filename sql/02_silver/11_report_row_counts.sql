-- The silver figures that feed the quality report and the slides.
SELECT 'matches (after deduplication)' AS metric, COUNT(*) AS value FROM `PROJECT.silver.matches`
UNION ALL SELECT 'finished',                 COUNTIF(status = 'finished')  FROM `PROJECT.silver.matches`
UNION ALL SELECT 'scheduled',                COUNTIF(status = 'scheduled') FROM `PROJECT.silver.matches`
UNION ALL SELECT 'team_matches',             COUNT(*) FROM `PROJECT.silver.team_matches`
UNION ALL SELECT 'h2h (bronze)',             COUNT(*) FROM `PROJECT.bronze.stored_matches_h2h`
UNION ALL SELECT 'h2h (strictly earlier)',   COUNT(*) FROM `PROJECT.silver.h2h`
UNION ALL SELECT 'match_weather',            COUNT(*) FROM `PROJECT.silver.match_weather`
UNION ALL SELECT 'match_goals',              COUNT(*) FROM `PROJECT.silver.match_goals`
UNION ALL SELECT 'player_match_stats',       COUNT(*) FROM `PROJECT.silver.player_match_stats`
UNION ALL SELECT 'teams',                    COUNT(*) FROM `PROJECT.silver.teams`
UNION ALL SELECT 'players',                  COUNT(*) FROM `PROJECT.silver.players`;
