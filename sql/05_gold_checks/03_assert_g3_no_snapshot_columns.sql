-- G3 (BLOCKING): none of these may ever appear in the feature table. They are either a
-- snapshot of the present (elo, rank, form string, season rates) or the result of the very
-- match being predicted.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.gold.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = 'match_features'
      AND column_name IN (
          'elo_rating', 'elo_rank', 'form_string', 'btts_rate',
          'over_2_5_rate', 'matches_played', 'score_home', 'score_away'
      )
) AS 'G3: snapshot column or own-match score present in gold.match_features';
