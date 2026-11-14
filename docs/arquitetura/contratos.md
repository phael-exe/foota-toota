# Contratos entre coleta, modelo e plataforma

Este documento é a fonte da verdade para quem integra com o pipeline de streaming do Foota Toota:
nomes de tópicos e assinaturas, formato de cada mensagem, tabelas, rotas e permissões. Ele foi
escrito para ser lido por pessoas e pelos agentes de código de cada integrante. Se algo aqui
mudar, muda primeiro aqui.

| Quem | Responsável por |
| --- | --- |
| Raphael | coletor, tópicos e assinaturas, Dataflow (que chama a API), tabelas `stream.*` e views da gold |
| André | modelo no Vertex AI Model Registry e API no Cloud Run (`/predict` e `/predict/lote`) |
| Wagner | plataforma: lê partidas e predições no BigQuery ou nos Parquet públicos |

## 1. Onde fica cada coisa

Tudo do pipeline mora no projeto **`pdm-bia-505511`**, inclusive a API do modelo. BigQuery na
multi-região `US`; Pub/Sub, Dataflow, Cloud Run e Scheduler em **`us-central1`**. A plataforma
conversa com o pipeline lendo o BigQuery (ou os Parquet públicos).

```
Football-Data.org ──> coletor (Cloud Run Job, a cada 5 min) ──> tópico eventos
                                                                   ├─ eventos-bigquery ──> stream.eventos_brutos   (bronze do stream)
                                                                   └─ eventos-dataflow ──> Dataflow ──> stream.partidas  (evento + predição)
                                                                                              │  ^     ├─> stream.partidas_rejeitadas
                                                     partidas agendadas, POST /predict/lote   │  │     └─> stream.predicoes_falhas
                                                                                              v  │
curl / Postman ──────────────────────────────────────────────────────────> API do modelo (Cloud Run, privada)

stream.partidas ──> gold.predicoes ──> gold.predicoes_avaliadas
```

| Recurso | Nome | Para quê |
| --- | --- | --- |
| Tópico | `eventos` | Eventos de partida (seção 2) |
| Tópico | `predicoes` | Histórico: a API publicava aqui antes de o Dataflow chamá-la. Nada novo chega |
| Assinatura | `eventos-dataflow` | Pull, consumida pelo Dataflow |
| Assinatura | `eventos-bigquery` | Grava o evento bruto em `stream.eventos_brutos` |
| Tabela | `stream.eventos_brutos` | Toda mensagem de `eventos` como chegou |
| Tabela | `stream.partidas` | Eventos validados pelo Dataflow, um por mudança de partida; os agendados com a predição |
| Tabela | `stream.partidas_rejeitadas` | Eventos recusados e o motivo |
| Tabela | `stream.predicoes_falhas` | Partidas agendadas que ficaram sem predição e o motivo |
| Tabela | `stream.predicoes` | Histórico das predições do tópico `predicoes` |
| View | `gold.partidas_unificadas` | Batch (silver) e stream lado a lado, coluna `origem` |
| View | `gold.partidas_atual` | Estado atual de cada partida: o que a plataforma lê |
| View | `gold.predicoes` | Uma linha por predição, com a prova de "antes do jogo" (seção 3) |
| View | `gold.predicoes_avaliadas` | Cada predição com o resultado real, quando houver |

## 2. Tópico `eventos`

**Quem publica:** o coletor (`streaming/producer.py`). Ninguém mais publica aqui.

**Quando:** no modo `live`, a cada 5 minutos o coletor consulta o Brasileirão Série A (`BSA`) no
Football-Data.org e publica só as partidas que mudaram (status, placar ou horário). No modo
`replay`, reproduz uma temporada já jogada, rodada por rodada (primeiro os agendados, depois os
resultados), para a demo.

**Corpo:** JSON UTF-8, um objeto por mensagem. **Atributos:** `mode` e `competition`, iguais aos
campos do corpo, para filtrar sem abrir a mensagem.

| Campo | Tipo | Nulo? | Descrição |
| --- | --- | --- | --- |
| `event_id` | string | não | Id da versão da partida: `<match_id>:<status>:<gols casa>-<gols fora>:<kickoff>`, com `:replay-<execução>` no replay. Mesma versão, mesmo id |
| `match_id` | string | não | `fdorg_<id>`. É o mesmo `match_id` das partidas agendadas em `silver.matches` e `gold.match_features` |
| `competition` | string | não | Código do Football-Data.org: `BSA`, `PL`, `CL`... |
| `season` | int | sim | Ano de início da temporada (`2026`) |
| `matchday` | int | sim | Rodada |
| `kickoff_utc` | string | não | ISO 8601 UTC, ex. `2026-10-17T21:00:00Z` |
| `status` | string | não | `SCHEDULED`, `TIMED`, `IN_PLAY`, `PAUSED`, `FINISHED`, `POSTPONED`, `SUSPENDED`, `CANCELLED`, `AWARDED` |
| `home_team_id` | string | não | Id do clube no Football-Data.org |
| `home_team_name` | string | sim | Nome no Football-Data.org (`CR Flamengo`) |
| `away_team_id` | string | não | Idem, visitante |
| `away_team_name` | string | sim | Idem, visitante |
| `score_home` | int | sim | Gols do mandante; nulo antes do jogo |
| `score_away` | int | sim | Gols do visitante; nulo antes do jogo |
| `source_id` | string | não | `football_data_org` |
| `source_updated_at` | string | sim | `lastUpdated` da API, ISO 8601 UTC |
| `mode` | string | não | `live` (dado real, agora) ou `replay` (reprodução para demo) |
| `published_at` | string | não | Quando o coletor publicou, ISO 8601 UTC com milissegundos |

Exemplo:

```json
{
  "event_id": "fdorg_555047:TIMED:-:2026-10-16T23:00:00Z",
  "match_id": "fdorg_555047",
  "competition": "BSA",
  "season": 2026,
  "matchday": 31,
  "kickoff_utc": "2026-10-16T23:00:00Z",
  "status": "TIMED",
  "home_team_id": "4364",
  "home_team_name": "Mirassol FC",
  "away_team_id": "6684",
  "away_team_name": "SC Internacional",
  "score_home": null,
  "score_away": null,
  "source_id": "football_data_org",
  "source_updated_at": "2026-10-16T00:20:34Z",
  "mode": "live",
  "published_at": "2026-10-16T13:14:13.512Z"
}
```

**Garantias e cuidados para quem consome:**

- Entrega **pelo menos uma vez**, sem ordem garantida. Use `event_id` para descartar repetidos.
- Uma partida encerrada não volta para agendada: o coletor bloqueia a regressão (a API às vezes
  responde de um cache antigo). Um placar corrigido de partida encerrada pode chegar.
- Para prever, interessam os eventos com `status` `TIMED` ou `SCHEDULED`. `FINISHED` traz o
  rótulo real.
- Eventos `replay` são partidas que já aconteceram. Servem para a demo; a plataforma não deve
  mostrá-los como jogo atual (a `gold.partidas_atual` já os exclui).

## 3. Predições

**Quem prevê:** o Dataflow, chamando a API do modelo. Para cada evento de partida **ainda não
iniciada** (`TIMED` ou `SCHEDULED`), ele manda `POST /predict/lote` (seção 4), em lotes de até
100, com `match_id`, `event_id`, `competition`, `season` e os ids dos clubes. Eventos de partida em
andamento ou encerrada não chamam a API: são o resultado real.

**Autenticação:** a API é privada. Os workers do Dataflow rodam com a conta padrão do Compute
(`<número do projeto>-compute@developer.gserviceaccount.com`), que tem `roles/run.invoker` no
serviço `modelo-api`, e mandam um ID token com audience igual à URL do serviço.
`streaming/dataflow.sh iniciar` dá a permissão e passa a URL.

**Novas tentativas:** timeout (60 s de leitura, para cobrir o cold start), erro de conexão, 429 e
5xx são tentados de novo, até 4 vezes no total, com espera de 1, 2 e 4 s. Num lote que volta 200,
só os itens com 429, 500 ou 503 são reenviados. 4xx não é tentado de novo.

**Onde a predição fica:** no próprio evento, em `stream.partidas`. A linha de um evento previsto
traz, além das colunas do evento:

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `prediction_id` | STRING | Igual para o mesmo evento e a mesma versão do modelo (UUID5) |
| `model_name` | STRING | Ex. `boosted_tree_brasileirao` |
| `model_version` | STRING | Versão no Vertex AI Model Registry |
| `prob_home`, `prob_draw`, `prob_away` | FLOAT64 | Probabilidades de cada resultado |
| `predicted_outcome` | STRING | `home`, `draw` ou `away`, os rótulos de `silver.matches.outcome` |
| `predicted_at` | TIMESTAMP | Quando a API respondeu |
| `features_ate` | TIMESTAMP | Instante do último dado usado nas features, quando a gold o traz |

Eventos sem predição têm essas colunas nulas.

**Falhas:** a partida agendada que fica sem predição chega em `stream.partidas` mesmo assim, e
ganha uma linha em `stream.predicoes_falhas` (`event_id`, `match_id`, `league_id`, `status`
HTTP, `motivo`, `tentativas`, `processed_at`). Motivos:

| Motivo | De onde vem |
| --- | --- |
| `sem_campeao`, `fora_da_gold`, `features_ausentes`, `pedido_invalido`, `indisponivel`, `erro_interno` | Da API (seção 4) |
| `timeout`, `conexao` | Do cliente: a API não respondeu ou cortou a resposta (`status` nulo) |
| `token` | O worker não conseguiu o ID token (`status` nulo) |
| `erro_cliente` | Erro inesperado no próprio pipeline ao chamar a API, ex. `--api_url` inválida (`status` nulo) |
| `nao_autorizado` | 401 ou 403: falta `run.invoker` para a conta dos workers |
| `resposta_invalida` | A API respondeu 200 num formato inesperado (sem `resultados`, item sem `prediction_id`, data ilegível) |
| `http_<status>` | Outro status sem motivo no corpo |

**Leitura:** `gold.predicoes` tem uma linha por `prediction_id` (o evento reentregue pelo Pub/Sub
repete o id e é descartado), no formato da tabela acima, mais `event_id`, `match_id`,
`league_id`, `kickoff_utc`, `mode` e a prova de que a predição veio antes do jogo:

| Coluna | Vale para | Significado |
| --- | --- | --- |
| `prevista_antes_do_jogo` | `live` | `predicted_at < kickoff_utc` |
| `features_antes_do_jogo` | `replay` | `features_ate < kickoff_utc`: o replay roda depois do jogo, então o que conta é as features pararem antes dele |

A exportação pública `gold/predictions.parquet` (`scripts/exportar_tabelas_publicas.sh`) sai de
`gold.predicoes`.

## 4. API do modelo

Um serviço Cloud Run (`modelo-api`, pacote `modelo/api/`) no `pdm-bia-505511`, **privado**:
quem chama precisa de `roles/run.invoker` e de `Authorization: Bearer <ID token>`. No
streaming, quem chama é o Dataflow, com a conta dos workers.

| Rota | Entrada | Saída |
| --- | --- | --- |
| `POST /predict` | Um pedido (abaixo) | A predição: `prediction_id`, `event_id`, `match_id`, `league_id` e as colunas da seção 3 |
| `POST /predict/lote` | `{"pedidos": [...]}`, de 1 a 100 pedidos | Sempre 200: `{"resultados": [{"match_id", "event_id", "status", "predicao", "motivo"}]}`, na ordem dos pedidos |
| `GET /health` | | Versão de cada modelo, `motivo` (`sem_campeao` quando não há versão aprovada), partidas carregadas |

**Pedido.** Só `match_id` é obrigatório.

| Campo | Para quê |
| --- | --- |
| `match_id` | A partida; procurada na gold de cada liga |
| `league_id` | Restringe a uma liga (id da silver) |
| `competition` | Código do Football-Data.org (`BSA`, `PL`...), quando não vem `league_id` |
| `event_id` | O evento que originou o pedido: com ele o `prediction_id` é determinístico (mesmo evento e mesma versão, mesmo id), então um retry não duplica predição |
| `season`, `home_team_id`, `away_team_id` | Acham a partida pelo confronto quando a gold a guarda com o id de outra fonte (o replay traz ids `fdorg_`, a gold pode ter `fduk_`) |
| `features` | Features diretas, para simular uma partida (pede `league_id`); as que faltam viram nulo |

**Erros.** Todo erro traz `{"detail": {"motivo", "mensagem"}}` (no lote, `status` e `motivo`
em cada item). Da API, só o `503` é passageiro; o Dataflow tenta de novo também `429` e `500`
(seção 3):

| Status | `motivo` | Quando |
| --- | --- | --- |
| 404 | `fora_da_gold` | A partida não está na gold |
| 409 | `sem_campeao` | A liga não tem versão com alias `campeao`, ou a competição não tem modelo |
| 409 | `features_ausentes` | O modelo pede uma coluna que a gold não tem: só se resolve com ação de alguém |
| 422 | `pedido_invalido` | `league_id` desconhecido, features diretas sem liga ou fora da lista do modelo |
| 500 | `erro_interno` | Erro inesperado num pedido; no lote, só aquele item |
| 503 | `indisponivel` | Gold ou Registry fora do ar (chamadas ao Registry com timeout de 30 s) |

**Features** vêm da gold pública (`gs://foota-toota-505511/gold/match_features_<liga>.parquet`),
relida a cada 10 minutos. `features_ate` é o instante do último dado usado nas features, quando a
gold traz a coluna; sem ela, `null`.

**Modelos.** O de cada liga é a versão com alias `campeao` no Vertex AI Model Registry do
`pdm-bia-505511`; mover o alias troca o modelo em até 10 minutos, sem deploy, e tirá-lo deixa a
liga sem predição. Cada versão é um diretório em `gs://pdm-bia-505511-modelos/` com
`model.joblib`, `features.json` (a lista ordenada de features que o modelo recebe) e
`metricas.json`.

**Treino** (`modelo/treinar.py`): hiperparâmetros escolhidos em EVAL, retreino em TRAIN + EVAL,
medida em TEST. Uma versão só ganha o alias `campeao` se bater, em TEST, o "sempre mandante"
(acurácia), as frequências do treino (log loss) e o campeão atual, reavaliado nas mesmas partidas
com as features dele. Empate não promove. Cada execução, aprovada ou não, vira um run no Vertex AI
Experiments `foota-toota-resultado`.

## 5. Plataforma (Wagner)

**Partidas e predições:** no BigQuery. Uma predição aparece em `gold.predicoes` segundos depois
de o evento agendado chegar ao Dataflow.

```sql
-- página de um jogo: estado atual (batch + stream, a versão mais nova)
SELECT * FROM `pdm-bia-505511.gold.partidas_atual`
WHERE league_id = 'brasileirao_serie_a' AND season = 2026 AND round = '31'
ORDER BY kickoff_utc;

-- predições de uma partida, da mais nova para a mais antiga
SELECT * FROM `pdm-bia-505511.gold.predicoes`
WHERE match_id = 'fdorg_555047'
ORDER BY predicted_at DESC;

-- acerto do modelo por versão
SELECT model_version, COUNT(*) AS n, AVG(IF(hit, 1, 0)) AS acerto
FROM `pdm-bia-505511.gold.predicoes_avaliadas`
WHERE hit IS NOT NULL
GROUP BY 1;
```

`gold.partidas_atual` tem uma linha por partida (`origem` diz se a versão mais nova veio do batch
ou do stream). Os ids de clube são os da silver (`Flamengo`, `Palmeiras`...), então batem com
`silver.teams` e com a gold.

Para ler o BigQuery de outro projeto, a conta de serviço do backend precisa de
`roles/bigquery.jobUser` no projeto e `roles/bigquery.dataViewer` em `stream`, `gold` e `silver`
(as views da gold leem a silver). O Raphael concede (`PLATAFORMA_SA=<email> streaming/infra.sh`).

**Bucket público**, sem conta no GCP: `https://storage.googleapis.com/foota-toota-505511/<arquivo>`.

| Arquivo | O que tem |
| --- | --- |
| `_manifest.json` | `version`, `exported_at` e linhas por arquivo. Baixe de novo só quando `version` mudar |
| `silver/teams.parquet` | Um clube por `team_id`, o mesmo de `matches`, `standings` e da gold, com o id de cada fonte, nome curto, sigla, país e escudo |
| `silver/matches.parquet` | Um jogo por linha, todas as ligas; jogos vistos por várias fontes aparecem uma vez |
| `silver/standings.parquet` | Classificação com o `team_id` canônico (`source_team_id` é o do Football-Data.org) |
| `silver/match_stats.parquet`, `silver/match_odds.parquet` | Sempre com um `match_id` que existe em `matches` |
| `gold/predictions.parquet` | `gold.predicoes` (seção 3) |

O bucket é reexportado a cada `scripts/atualizar_partidas.sh`, que coleta partidas e classificação
na mesma rodada.

## 6. O que cada um manda para o Raphael

| Quem | O quê | Para |
| --- | --- | --- |
| Wagner | E-mail da conta de serviço do backend | Permissão de leitura no BigQuery |

## 7. Decisões do grupo (16/10)

- **Um modelo por liga.** O `model_name` diz a liga, ex. `boosted_tree_brasileirao` e
  `boosted_tree_epl`; a gold já tem uma tabela de features por liga
  (`gold.match_features_brasileirao` e `gold.match_features_epl`).
- **Ligas: Brasileirão e Premier League.** O stream ao vivo cobre o **Brasileirão**: os eventos,
  a silver e a gold usam o mesmo `match_id` (`fdorg_...`) nas partidas agendadas. A **Premier
  League** está só no batch, com ids da Big Balls (outros ids, sem de-para com o Football-Data.org)
  e dados até 06/09. Na demo, a EPL entra pelo `/predict` com o `match_id` da gold; levar a EPL
  para o stream exige um de-para de clubes e partidas que ainda não existe.
- **O `match_id` da predição é o do evento.** Depois que um jogo do Brasileirão termina, a silver
  pode passar a guardá-lo com o id de outra fonte; a `gold.predicoes_avaliadas` já cobre isso,
  porque pega o resultado pelo id do stream.
- **Região:** tudo o que é regional em `us-central1` (Pub/Sub, Dataflow, Cloud Run, Scheduler). O
  BigQuery fica na multi-região `US`, que inclui `us-central1`; é onde está o batch.

## 8. Operação

| Tarefa | Comando |
| --- | --- |
| Criar ou conferir a infraestrutura | `streaming/infra.sh` |
| Ligar o Dataflow (cobra por hora) | DAG `dataflow_liga_desliga` com `ligar`, ou `streaming/dataflow.sh iniciar` |
| Desligar o Dataflow | DAG `dataflow_liga_desliga` com `desligar`, ou `streaming/dataflow.sh parar` |
| Publicar o coletor ao vivo | `streaming/deploy_coletor.sh` (o agendamento é do DAG `coleta_ao_vivo`) |
| Coleta sem o Airflow (VM parada) | `streaming/deploy_coletor.sh retomar` / `pausar` (Cloud Scheduler) |
| Replay de rodadas para a demo | DAG `disparar_eventos`, ou `uv run python streaming/producer.py replay --rodadas 28-30 --intervalo 1` |
| Ver eventos sem publicar | `uv run python streaming/producer.py --sem-publicar replay --rodadas 30 --intervalo 0` |
| Atualizar o batch (bronze -> gold) | `scripts/atualizar_partidas.sh` |
| Treinar, avaliar e registrar os modelos | `uv run --no-project --with-requirements modelo/requirements-treino.txt python modelo/treinar.py` |
| Publicar a API do modelo | `modelo/deploy_api.sh` |

Com o Dataflow desligado nada se perde: os eventos continuam caindo em `stream.eventos_brutos` e
esperam até 7 dias na assinatura `eventos-dataflow`, processados quando o job volta.
