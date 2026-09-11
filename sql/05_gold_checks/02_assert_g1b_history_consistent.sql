-- G1b (BLOCKING): the audit trail must agree with itself. Counts match array lengths,
-- nothing exceeds five matches, no recorded kickoff reaches the target, and
-- has_full_history is exactly what its definition says.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.gold.match_features`
    WHERE home_history_count <> ARRAY_LENGTH(home_history_match_ids)
       OR away_history_count <> ARRAY_LENGTH(away_history_match_ids)
       OR home_history_count > 5
       OR away_history_count > 5
       OR home_history_latest_kickoff_utc >= kickoff_utc
       OR away_history_latest_kickoff_utc >= kickoff_utc
       OR has_full_history <> (home_history_count = 5 AND away_history_count = 5)
) AS 'G1b: inconsistent audit trail (count, array length, dates or has_full_history)';
