-- The next ten fixtures, the way they go on the slide.
SELECT
    FORMAT_TIMESTAMP('%d/%m %H:%M', kickoff_utc) AS kickoff,
    home_team,
    away_team,
    prediction,
    p_home,
    p_draw,
    p_away
FROM `PROJECT.gold.predictions`
ORDER BY kickoff_utc
LIMIT 10;
