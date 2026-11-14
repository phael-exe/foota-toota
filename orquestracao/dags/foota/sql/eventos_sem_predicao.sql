-- Eventos de jogo agendado que chegaram ao tópico eventos desde @desde, há mais de @limite_min
-- minutos, e ainda não saíram do Dataflow: não estão em stream.partidas (com ou sem predição)
-- nem em stream.partidas_rejeitadas. Só faz sentido com o job rodando: drenado, os eventos
-- esperam na assinatura de propósito.
SELECT
    COUNT(*)            AS pendentes,
    MIN(b.publish_time) AS mais_antigo
FROM `PROJECT.stream.eventos_brutos` AS b
WHERE b.publish_time >= @desde
    AND b.publish_time < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @limite_min MINUTE)
    AND JSON_VALUE(b.data, '$.status') IN ('SCHEDULED', 'TIMED')
    AND NOT EXISTS (
        SELECT 1
        FROM `PROJECT.stream.partidas` AS p
        WHERE p.event_id = JSON_VALUE(b.data, '$.event_id')
    )
    AND NOT EXISTS (
        SELECT 1
        FROM `PROJECT.stream.partidas_rejeitadas` AS r
        WHERE r.event_id = JSON_VALUE(b.data, '$.event_id')
    )
