-- G2 (BLOCKING): head-to-head history may only contain strictly earlier meetings.
-- This is the first line of defence against leakage into the model.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.h2h` h
    JOIN `PROJECT.silver.matches` m
      ON m.match_id = h.for_match_id
    WHERE h.match_date >= m.kickoff_utc
       OR h.match_id = h.for_match_id
) AS 'G2: h2h contains the match itself or a later meeting';
