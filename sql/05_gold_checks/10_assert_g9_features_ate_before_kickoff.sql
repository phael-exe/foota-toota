-- G9 (BLOCKING): features_ate is the instant of the last data behind a row's features, the
-- latest earlier match of either team, and it is always before the kickoff. A prediction carries
-- it as the proof that it used nothing from the match itself.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.gold.match_features`
    WHERE features_ate >= kickoff_utc
       OR features_ate IS DISTINCT FROM GREATEST(
              COALESCE(home_history_latest_kickoff_utc, away_history_latest_kickoff_utc),
              COALESCE(away_history_latest_kickoff_utc, home_history_latest_kickoff_utc)
          )
) AS 'G9: features_ate missing, inconsistent with the history or not before the kickoff';
