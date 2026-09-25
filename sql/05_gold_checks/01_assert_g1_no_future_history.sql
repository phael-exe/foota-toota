-- G1 (BLOCKING): the leakage check. Every match named in a history array must have kicked
-- off strictly before the target match and must already be finished.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.gold.match_features` f,
         UNNEST(ARRAY_CONCAT(
             f.home_history_match_ids,
             f.away_history_match_ids,
             f.extra_history_match_ids
         )) AS hist_id
    JOIN `PROJECT.silver.matches` h
      ON h.match_id = hist_id
    WHERE h.kickoff_utc >= f.kickoff_utc
       OR h.status <> 'finished'
) AS 'G1: attribute derived from a match at or after the target match';
