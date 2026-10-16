-- Each prediction next to the real result once the match ends: the labels that arrive through
-- the stream close the MLOps loop (hit rate per model version, round by round). The result
-- comes from the latest finished live event of that match id, else from silver.
--   SELECT model_version, AVG(IF(hit, 1, 0)) FROM gold.predicoes_avaliadas
--   WHERE hit IS NOT NULL GROUP BY 1
CREATE OR REPLACE VIEW `PROJECT.gold.predicoes_avaliadas` AS
WITH stream_result AS (
    SELECT match_id, outcome
    FROM `PROJECT.stream.partidas`
    WHERE mode = 'live' AND status = 'finished'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY published_at DESC) = 1
),
batch_result AS (
    SELECT match_id, outcome
    FROM `PROJECT.silver.matches`
    WHERE status = 'finished'
)
SELECT
    p.*,
    COALESCE(r.outcome, b.outcome) AS real_outcome,
    IF(COALESCE(r.outcome, b.outcome) IS NULL, NULL,
       p.predicted_outcome = COALESCE(r.outcome, b.outcome)) AS hit
FROM `PROJECT.stream.predicoes` p
LEFT JOIN stream_result r ON r.match_id = p.match_id
LEFT JOIN batch_result b ON b.match_id = p.match_id;
