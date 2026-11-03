-- S19 (BLOCKING): Fantasy Premier League gameweek minutes must be within physical match limits [0, 120].
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.player_gameweeks`
    WHERE minutes_played < 0
       OR minutes_played > 120
) AS 'S19: invalid player minutes played in silver.player_gameweeks';
