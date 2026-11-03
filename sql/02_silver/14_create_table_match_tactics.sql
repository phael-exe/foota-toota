-- Match tactical context fact table (formations, head coaches, arena).
-- Sourced from Brasileirao Historico dataset (2003-2026).

CREATE OR REPLACE TABLE `PROJECT.silver.match_tactics` AS
SELECT
    CONCAT('bra_', ID) AS match_id,
    `PROJECT.silver.blank_to_null`(formacao_mandante) AS home_formation,
    `PROJECT.silver.blank_to_null`(formacao_visitante) AS away_formation,
    `PROJECT.silver.blank_to_null`(tecnico_mandante) AS home_coach,
    `PROJECT.silver.blank_to_null`(tecnico_visitante) AS away_coach,
    `PROJECT.silver.blank_to_null`(arena) AS stadium_name,
    `PROJECT.silver.blank_to_null`(mandante_Estado) AS home_state,
    `PROJECT.silver.blank_to_null`(visitante_Estado) AS away_state,
    CURRENT_TIMESTAMP() AS transformed_at
FROM `PROJECT.bronze.brasileirao_historico`
WHERE ID IS NOT NULL;
