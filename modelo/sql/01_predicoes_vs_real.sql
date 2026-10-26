-- Predição x resultado real, uma linha por partida, no projeto dos modelos.
-- A chave é o match_id do evento (`fdorg_...`), o mesmo antes do jogo, quando
-- o modelo prevê, e depois, quando chega o evento FINISHED com o placar.
-- A API (modelo/api.py, classe Avaliacao) grava os dois lados com MERGE, em
-- qualquer ordem; a chave primária só é declarada (o BigQuery não a impõe),
-- quem garante uma linha por partida é o MERGE. `hit` fica nulo até os dois
-- lados existirem. Criada uma vez por modelo/deploy_api.sh.
CREATE SCHEMA IF NOT EXISTS `PROJECT.modelo`
OPTIONS (
    location = 'US',
    description = 'Laboratório de modelos do Foota Toota'
);

CREATE TABLE IF NOT EXISTS `PROJECT.modelo.predicoes_vs_real` (
    match_id          STRING    NOT NULL OPTIONS (description = 'Id do evento, fdorg_<id>'),
    league_id         STRING,
    competition       STRING,
    season            INT64,
    matchday          INT64,
    kickoff_utc       TIMESTAMP,
    home_team_id      STRING    OPTIONS (description = 'Id do Football-Data.org'),
    home_team_name    STRING,
    away_team_id      STRING,
    away_team_name    STRING,
    mode              STRING    OPTIONS (description = 'live ou replay'),
    prediction_id     STRING,
    event_id          STRING    OPTIONS (description = 'Evento que disparou a predição'),
    model_name        STRING,
    model_version     STRING,
    prob_home         FLOAT64,
    prob_draw         FLOAT64,
    prob_away         FLOAT64,
    predicted_outcome STRING    OPTIONS (description = 'home, draw ou away'),
    predicted_at      TIMESTAMP,
    score_home        INT64,
    score_away        INT64,
    real_outcome      STRING    OPTIONS (description = 'home, draw ou away, pelo placar final'),
    result_event_id   STRING    OPTIONS (description = 'Evento FINISHED que trouxe o placar'),
    result_at         TIMESTAMP,
    hit               BOOL      OPTIONS (description = 'predicted_outcome = real_outcome'),
    updated_at        TIMESTAMP,
    PRIMARY KEY (match_id) NOT ENFORCED
)
CLUSTER BY league_id
OPTIONS (description = 'Predição do modelo x resultado real, uma linha por partida');
