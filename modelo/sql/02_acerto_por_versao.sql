-- Como cada versão de modelo está indo nas partidas que já acabaram, a partir de
-- modelo.predicoes_vs_real. Só entram linhas com os dois lados (predição e
-- resultado); `mode` separa o replay da demo do ao vivo. Tem as mesmas medidas
-- do treino (modelo/treinar.py) e o "sempre mandante" nas mesmas partidas,
-- para comparar com o que o modelo mostrou em TEST.
--   SELECT * FROM `PROJECT.modelo.acerto_por_versao` ORDER BY league_id, mode
CREATE OR REPLACE VIEW `PROJECT.modelo.acerto_por_versao`
OPTIONS (description = 'Acerto, log loss e baseline por versão de modelo e modo') AS
SELECT
    league_id,
    model_name,
    model_version,
    mode,
    COUNT(*) AS partidas,
    COUNTIF(hit) AS acertos,
    ROUND(AVG(IF(hit, 1, 0)), 4) AS acuracia,
    ROUND(AVG(-LN(GREATEST(
        CASE real_outcome
            WHEN 'home' THEN prob_home
            WHEN 'draw' THEN prob_draw
            ELSE prob_away
        END, 1e-15))), 4) AS log_loss,
    ROUND(AVG(IF(real_outcome = 'home', 1, 0)), 4) AS acuracia_sempre_mandante,
    MIN(kickoff_utc) AS primeira_partida,
    MAX(kickoff_utc) AS ultima_partida,
    MAX(updated_at) AS atualizado_em
FROM `PROJECT.modelo.predicoes_vs_real`
WHERE hit IS NOT NULL
GROUP BY league_id, model_name, model_version, mode;
