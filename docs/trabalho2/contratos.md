# Trabalho 2: contratos entre coleta, modelo e plataforma

Este documento é a fonte da verdade para quem integra com o pipeline de streaming do Foota Toota:
nomes de tópicos e assinaturas, formato de cada mensagem, tabelas, rotas e permissões. Ele foi
escrito para ser lido por pessoas e pelos agentes de código de cada integrante. Se algo aqui
mudar, muda primeiro aqui.

Visão geral e divisão de tarefas: `Foota-Toota-Trabalho-2-Arquitetura.pdf`.

| Quem | Responsável por |
| --- | --- |
| Raphael | coletor, tópicos e assinaturas, Dataflow, tabelas `stream.*` e views da gold |
| André | modelo no Vertex AI Model Registry e API no Cloud Run (`/predict` e `/pubsub`) |
| Wagner | plataforma: recebe as predições por push e lê o histórico no BigQuery |

## 1. Onde fica cada coisa

Tudo do pipeline mora no projeto **`pdm-bia-505511`**. BigQuery na multi-região `US`; Pub/Sub,
Dataflow, Cloud Run e Scheduler em **`us-central1`**. A API do André e o backend do Wagner podem
ficar nos projetos de vocês: a conversa com o pipeline é só por HTTP (push do Pub/Sub) e por
leitura no BigQuery.

```
Football-Data.org ──> coletor (Cloud Run Job, a cada 5 min) ──> tópico eventos
                                                                   ├─ eventos-bigquery ──> stream.eventos_brutos   (bronze do stream)
                                                                   ├─ eventos-dataflow ──> Dataflow ──> stream.partidas  (silver do stream)
                                                                   │                                └─> stream.partidas_rejeitadas
                                                                   └─ eventos-api (push) ──> API do André  POST /pubsub
                                                                                                │ publica
curl / Postman ──> API do André  POST /predict                                                  v
                                                                                           tópico predicoes
                                                                   ├─ predicoes-bigquery ──> stream.predicoes  (falhas -> predicoes-dlq)
                                                                   └─ predicoes-plataforma (push) ──> backend do Wagner
```

| Recurso | Nome | Para quê |
| --- | --- | --- |
| Tópico | `eventos` | Eventos de partida (seção 2) |
| Tópico | `predicoes` | Predições do modelo (seção 3) |
| Tópico | `predicoes-dlq` | Predições que o BigQuery recusou 5 vezes |
| Assinatura | `eventos-dataflow` | Pull, consumida pelo Dataflow |
| Assinatura | `eventos-bigquery` | Grava o evento bruto em `stream.eventos_brutos` |
| Assinatura | `eventos-api` | Push para `POST /pubsub` do André (criada quando a URL existir) |
| Assinatura | `predicoes-bigquery` | Grava a predição em `stream.predicoes` |
| Assinatura | `predicoes-plataforma` | Push para o backend do Wagner (criada quando a URL existir) |
| Assinatura | `predicoes-dlq-sub` | Pull, para inspecionar predições recusadas |
| Tabela | `stream.eventos_brutos` | Toda mensagem de `eventos` como chegou |
| Tabela | `stream.partidas` | Eventos validados pelo Dataflow, um por mudança de partida |
| Tabela | `stream.partidas_rejeitadas` | Eventos recusados e o motivo |
| Tabela | `stream.predicoes` | Histórico de predições |
| View | `gold.partidas_unificadas` | Batch (silver) e stream lado a lado, coluna `origem` |
| View | `gold.partidas_atual` | Estado atual de cada partida: o que a plataforma lê |
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

### Push para a API do André (`eventos-api`)

O Pub/Sub faz `POST` na URL cadastrada com este envelope (o evento vai em base64 em `data`;
abaixo, abreviado):

```json
{
  "message": {
    "data": "eyJldmVudF9pZCI6ICJmZG9yZ181NTUwNDc6VElNRUQ6LToyMDI2LTEwLTE2VDIzOjAwOjAwWiIsIC4uLn0=",
    "attributes": {"mode": "live", "competition": "BSA"},
    "messageId": "17702301744963958",
    "publishTime": "2026-10-16T13:14:13.664Z"
  },
  "subscription": "projects/pdm-bia-505511/subscriptions/eventos-api"
}
```

- Responda **2xx em até 60 s** para confirmar. Qualquer outra resposta faz o Pub/Sub tentar de
  novo, com espera crescente.
- Evento que você decide ignorar (ex. `FINISHED`) ou que não consegue ler: responda **204**
  mesmo assim, senão ele volta para sempre. Responda 5xx só em falha passageira sua.

## 3. Tópico `predicoes`

**Quem publica:** a API do André, uma mensagem por predição. **Quem consome:** a assinatura
BigQuery `predicoes-bigquery` (grava em `stream.predicoes`) e o push `predicoes-plataforma`.

**Corpo:** JSON UTF-8. Cada campo cai na coluna de mesmo nome em `stream.predicoes`; campos que
não existem na tabela são descartados. Uma mensagem que viola a tabela (campo obrigatório ausente,
tipo errado) é tentada 5 vezes e vai para `predicoes-dlq`; veja com
`gcloud pubsub subscriptions pull predicoes-dlq-sub --project=pdm-bia-505511 --auto-ack`.

| Campo | Tipo | Nulo? | Descrição |
| --- | --- | --- | --- |
| `prediction_id` | string | não | Único por predição, ex. UUID4 |
| `event_id` | string | sim | `event_id` do evento que disparou a predição; nulo se veio do `/predict` |
| `match_id` | string | não | O `match_id` do evento (`fdorg_...`) |
| `league_id` | string | sim | `brasileirao_serie_a`, `epl`... (ids da silver) |
| `model_name` | string | não | Ex. `boosted_tree_brasileirao` |
| `model_version` | string | não | Versão no Vertex AI Model Registry |
| `prob_home` | float | sim | Probabilidade de vitória do mandante |
| `prob_draw` | float | sim | Probabilidade de empate |
| `prob_away` | float | sim | Probabilidade de vitória do visitante |
| `predicted_outcome` | string | não | `home`, `draw` ou `away` |
| `predicted_at` | string | não | ISO 8601 UTC, ex. `2026-10-16T13:15:02Z` |

Exemplo (o formato foi validado no ar em 16/10 com uma mensagem de teste):

```json
{
  "prediction_id": "6f0c3c7e-2f7e-4b8f-9a55-0d6c2f1e9a10",
  "event_id": "fdorg_555047:TIMED:-:2026-10-16T23:00:00Z",
  "match_id": "fdorg_555047",
  "league_id": "brasileirao_serie_a",
  "model_name": "boosted_tree_brasileirao",
  "model_version": "1",
  "prob_home": 0.48,
  "prob_draw": 0.29,
  "prob_away": 0.23,
  "predicted_outcome": "home",
  "predicted_at": "2026-10-16T13:15:02Z"
}
```

Os rótulos `home`, `draw` e `away` são os mesmos de `silver.matches.outcome`, o que permite a
`gold.predicoes_avaliadas` comparar predição e resultado sem tradução.

## 4. API do modelo (André)

Um serviço Cloud Run com duas rotas, as duas chamando a mesma função de predição:

| Rota | Quem chama | Entrada | Saída |
| --- | --- | --- | --- |
| `POST /predict` | curl/Postman na demo (vale 30% da nota) | JSON com os dados da partida | A predição, no formato da seção 3, em JSON |
| `POST /pubsub` | Push da assinatura `eventos-api` | Envelope da seção 2 | 204; publica a predição em `predicoes` |

Sugestão para a entrada do `/predict`: aceitar `{"match_id": "fdorg_555047"}` e buscar as features
em `gold.match_features` (as partidas agendadas do Brasileirão estão lá com `split_set = 'PREDICT'`
e o mesmo `match_id` dos eventos), ou receber as features diretamente. A escolha é do André; o
formato da **saída** é o da seção 3, para o `/predict` e o tópico falarem a mesma língua.

**Dados de treino**, um arquivo por liga, com as features da gold e três rótulos
(`label_outcome`, `label_goals_home`, `label_goals_away`):
`https://storage.googleapis.com/foota-toota-505511/gold/match_training_brasileirao.parquet` e
`.../gold/match_training_epl.parquet`. Use `split_set` (`TRAIN`, `EVAL`, `TEST`, `PREDICT`); as
linhas `PREDICT` são os jogos a prever, sem rótulo. Os gols são só rótulo, nunca feature.

Para publicar em `predicoes` de outro projeto, a conta de serviço do Cloud Run precisa de
`roles/pubsub.publisher` no tópico. O Raphael concede (`MODELO_SA=<email> streaming/infra.sh`).

## 5. Plataforma (Wagner)

**Ao vivo:** uma rota HTTPS no backend recebe o push de `predicoes-plataforma`, com o envelope da
seção 2 (a predição em base64 em `message.data`). Mesmas regras: 2xx confirma, o resto repete.

**Histórico e estado das partidas:** no BigQuery.

```sql
-- página de um jogo: estado atual (batch + stream, a versão mais nova)
SELECT * FROM `pdm-bia-505511.gold.partidas_atual`
WHERE league_id = 'brasileirao_serie_a' AND season = 2026 AND round = '31'
ORDER BY kickoff_utc;

-- predições de uma partida, da mais nova para a mais antiga
SELECT * FROM `pdm-bia-505511.stream.predicoes`
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

## 6. O que cada um manda para o Raphael

| Quem | O quê | Para |
| --- | --- | --- |
| André | URL pública da rota `/pubsub` | Criar a assinatura push `eventos-api` |
| André | E-mail da conta de serviço do Cloud Run | Permissão de publicar em `predicoes` |
| Wagner | URL pública da rota que recebe as predições | Criar a assinatura push `predicoes-plataforma` |
| Wagner | E-mail da conta de serviço do backend | Permissão de leitura no BigQuery |

### Autenticação do push

Todo push sai com um token OIDC no cabeçalho `Authorization: Bearer <token>`, assinado pela conta
**`pubsub-push@pdm-bia-505511.iam.gserviceaccount.com`**. Para conferir que a chamada veio do
nosso Pub/Sub, valide o token como um ID token do Google e confira:

- `email` = `pubsub-push@pdm-bia-505511.iam.gserviceaccount.com` e `email_verified` = `true`;
- `aud` = a URL exata do endpoint que vocês nos passaram.

Há dois jeitos de fazer isso no Cloud Run. Se o serviço exige autenticação, liberem
`roles/run.invoker` para essa conta e o próprio Cloud Run valida o token. Se o serviço é público
(`--allow-unauthenticated`), validem no código, por exemplo com
`google.oauth2.id_token.verify_oauth2_token` em Python.

## 7. Decisões do grupo (16/10)

- **Apresentação: no máximo 10 minutos** (enunciado do T2 e slide 57). Os 5 minutos eram do T1.
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
  BigQuery fica na multi-região `US`, que inclui `us-central1`; é onde está o batch do T1.

## 8. Operação

| Tarefa | Comando |
| --- | --- |
| Criar ou conferir a infraestrutura | `streaming/infra.sh` |
| Ligar o Dataflow (cobra por hora) | `streaming/dataflow.sh iniciar` |
| Desligar o Dataflow | `streaming/dataflow.sh parar` |
| Publicar o coletor ao vivo | `streaming/deploy_coletor.sh` |
| Pausar ou retomar a coleta | `streaming/deploy_coletor.sh pausar` / `retomar` |
| Replay de rodadas para a demo | `uv run python streaming/producer.py replay --rodadas 28-30 --intervalo 1` |
| Ver eventos sem publicar | `uv run python streaming/producer.py --sem-publicar replay --rodadas 30 --intervalo 0` |
| Atualizar o batch (bronze -> gold) | `scripts/atualizar_partidas.sh` |

Com o Dataflow desligado nada se perde: os eventos continuam caindo em `stream.eventos_brutos` e
esperam até 7 dias na assinatura `eventos-dataflow`, processados quando o job volta.
