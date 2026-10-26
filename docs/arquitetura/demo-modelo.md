# Demo da parte do modelo (André)

Roteiro da demonstração do modelo: `/predict` ao vivo, o stream gravando predição x real, e o
ciclo de MLOps no Vertex AI. Contrato e arquitetura: [`contratos.md`](contratos.md).

API: `https://modelo-api-3gvoh2dyuq-uc.a.run.app` (Cloud Run `modelo-api`, projeto `pdm-andre-2026`).

## Antes da demonstração

- **Na véspera, com o Raphael:** gold atualizada (`scripts/atualizar_partidas.sh`, para as features
  das próximas rodadas incluírem os jogos do fim de semana), assinatura `eventos-api` criada e
  permissão de publicar em `predicoes` (`EVENTOS_PUSH_URL=... MODELO_SA=... streaming/infra.sh`).
- **Na véspera:** rodar um replay (seção 2) uma vez. A tabela predição x real guarda o resultado; se
  algo falhar na hora, ela já tem o que mostrar.
- **Cinco minutos antes:** acordar o serviço. Ele dorme quando ninguém usa, e na volta carrega a gold
  e os modelos antes de responder (alguns segundos). Tem de mostrar `"versao": "1"` e `partidas`
  acima de zero nas duas ligas:

  ```bash
  curl -s https://modelo-api-3gvoh2dyuq-uc.a.run.app/health
  ```

- **Abas abertas** (projeto `pdm-andre-2026`):
  - [Cloud Run: logs do modelo-api](https://console.cloud.google.com/run/detail/us-central1/modelo-api/logs?project=pdm-andre-2026)
  - [Vertex AI Model Registry](https://console.cloud.google.com/vertex-ai/models?project=pdm-andre-2026)
  - [Vertex AI Experiments](https://console.cloud.google.com/vertex-ai/experiments?project=pdm-andre-2026)
  - [BigQuery: dataset `modelo`](https://console.cloud.google.com/bigquery?project=pdm-andre-2026&p=pdm-andre-2026&d=modelo&page=dataset)

## 1. `/predict`

Cruzeiro x Remo, Brasileirão, rodada 32, sexta 23/10 às 20h (Brasília):

```bash
curl -s -X POST https://modelo-api-3gvoh2dyuq-uc.a.run.app/predict \
  -H 'Content-Type: application/json' \
  -d '{"match_id": "fdorg_555052"}'
```

No PowerShell (o `curl` de lá é outro comando):

```powershell
Invoke-RestMethod -Method Post -Uri https://modelo-api-3gvoh2dyuq-uc.a.run.app/predict `
  -ContentType 'application/json' -Body '{"match_id": "fdorg_555052"}'
```

No Postman: `POST` na mesma URL, corpo `raw` JSON `{"match_id": "fdorg_555052"}`.

O que mostrar na resposta: as três probabilidades, `predicted_outcome`, `model_version` (a versão
do Vertex AI Model Registry que respondeu) e o `match_id`, que é o mesmo dos eventos do stream. A
predição também é publicada no tópico `predicoes` (o cabeçalho `X-Publicada` diz se foi), então a
plataforma do Wagner recebe por push.

Premier League, Chelsea x Tottenham, sábado 24/10. A EPL está só no batch, com dados até 06/09:

```bash
curl -s -X POST https://modelo-api-3gvoh2dyuq-uc.a.run.app/predict \
  -H 'Content-Type: application/json' \
  -d '{"match_id": "2aa61d11-c18e-42eb-a33f-75146aaa4fd1"}'
```

Simulação, para mostrar que o modelo reage às features (mandante bem melhor na temporada):

```bash
curl -s -X POST https://modelo-api-3gvoh2dyuq-uc.a.run.app/predict \
  -H 'Content-Type: application/json' \
  -d '{"match_id": "simulada", "league_id": "brasileirao_serie_a", "publicar": false,
       "features": {"home_avg_points_season": 2.3, "away_avg_points_season": 0.8,
                    "diff_avg_points_season": 1.5, "home_avg_points_last_5": 2.4,
                    "away_avg_points_last_5": 0.6, "diff_avg_points_last_5": 1.8}}'
```

Outras partidas da rodada 32 para pedir: `fdorg_555056` (Palmeiras x Bragantino), `fdorg_555058`
(Vasco x Corinthians), `fdorg_555054` (Internacional x Botafogo).

## 2. Stream: evento, predição e resultado na mesma linha

O Raphael solta um replay de uma rodada já jogada: primeiro os 10 jogos como agendados, depois os 10
resultados, um evento por segundo.

```bash
uv run python streaming/producer.py replay --rodadas 30 --intervalo 1
```

Cada evento chega na API pelo push da assinatura `eventos-api`. Nos logs do Cloud Run aparecem
`fdorg_... -> home (boosted_tree_brasileirao v1)` para cada predição e `fdorg_...: resultado away`
para cada placar. Pelo terminal:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="modelo-api" AND (textPayload:" -> " OR textPayload:"resultado")' \
  --project=pdm-andre-2026 --freshness=10m --format="value(timestamp,textPayload)"
```

Depois, no BigQuery: uma linha por partida, com a predição feita antes e o placar que chegou depois,
pelo mesmo `match_id`:

```sql
SELECT match_id, home_team_name, away_team_name, predicted_outcome,
       ROUND(prob_home, 2) AS casa, ROUND(prob_draw, 2) AS empate, ROUND(prob_away, 2) AS fora,
       score_home, score_away, real_outcome, hit
FROM `pdm-andre-2026.modelo.predicoes_vs_real`
WHERE mode = 'replay'
ORDER BY kickoff_utc;

SELECT * FROM `pdm-andre-2026.modelo.acerto_por_versao`;
```

Se perguntarem: no replay a gold guarda esses jogos com o id da Football-Data.co.uk (`fduk_...`),
não com o `fdorg_` do evento. A API acha a partida pelo confronto (temporada, mandante, visitante),
com um de-para de clubes tirado do bronze, e grava tudo com o `match_id` do evento.

## 3. MLOps: Registry, Experiments e a regra de promoção

- **Model Registry:** `boosted_tree_brasileirao` e `boosted_tree_epl`, versão 1 com o alias
  `campeao`. A API serve a versão que tem o alias e confere a cada 10 minutos: promover outra versão
  é mover o alias, sem novo deploy.
- **Experiments** (`foota-toota-resultado`): um run por liga e execução. Dois aprovados (a versão 1)
  e dois reprovados: o retreino nos mesmos dados empatou com o campeão, e empate não promove.
- **A regra** (`modelo/treinar.py`): hiperparâmetros escolhidos em EVAL, retreino em TRAIN + EVAL,
  medida em TEST, que não entra em nenhuma escolha. Só vira campeão quem bate, em TEST, o "sempre
  mandante" (acurácia), as frequências do treino (log loss) e o campeão atual nas mesmas partidas.
- Treinar de novo leva uns 9 minutos: não é para a hora. Se quiserem ver, o comando é
  `uv run --no-project --with-requirements modelo/requirements-treino.txt python modelo/treinar.py`.

### Números (TEST, versão 1)

| | Brasileirão | Premier League |
| --- | --- | --- |
| Partidas | 669 | 407 |
| Acurácia do modelo | 50,1% | 45,0% |
| Sempre mandante | 49,3% | 41,5% |
| Log loss do modelo | 1,012 | 1,060 |
| Log loss das frequências | 1,044 | 1,093 |

No Brasileirão a acurácia passa o "sempre mandante" por menos de um ponto, dentro do ruído para 669
partidas; o ganho que conta é a log loss, a qualidade das probabilidades que a plataforma mostra. Na
EPL o ganho aparece nas duas medidas. Empate quase nunca é o resultado mais provável: o modelo do
Brasileirão aponta empate em 10 das partidas de TEST (e o mandante em umas 625), o da EPL em
nenhuma, como no antigo modelo do BigQuery ML. A probabilidade de empate está na resposta, só
raramente é a maior.

## Se algo falhar

| Sintoma | O que fazer |
| --- | --- |
| Primeira chamada demora | O serviço estava dormindo; o `/health` antes resolve |
| `X-Publicada: false` | Falta a permissão de publicar em `predicoes` (Raphael, `MODELO_SA`). A predição volta igual |
| Replay não aparece nos logs | A assinatura `eventos-api` não existe ou aponta para outra URL; mostrar a tabela do replay da véspera |
| `404` no `/predict` | O `match_id` não está na gold; usar um dos ids acima |
| `503` | Modelo ou gold indisponível; `/health` mostra qual |
