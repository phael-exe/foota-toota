-- Scheduled matches the pipeline could not get a prediction for, with the reason: the API's
-- own (sem_campeao, fora_da_gold, features_ausentes...) or the client's (timeout, conexao,
-- nao_autorizado, resposta_invalida, http_<status>). The match itself still lands in
-- stream.partidas, without prediction. status is the HTTP status, NULL on timeout/connection.
-- Partitioned by DATE(processed_at). Created once.
CREATE TABLE IF NOT EXISTS `PROJECT.stream.predicoes_falhas` (
    event_id     STRING,
    match_id     STRING    NOT NULL,
    league_id    STRING,
    status       INT64,
    motivo       STRING    NOT NULL,
    tentativas   INT64     NOT NULL,
    processed_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(processed_at)
OPTIONS (description = 'Partidas agendadas sem predição e o motivo');
