# API do modelo em módulos, no projeto único — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A API do modelo vira um pacote com módulos pequenos, para de receber push e de publicar no Pub/Sub, ganha o contrato que o Dataflow vai usar (lote, motivos de falha, `features_ate`, lista de features por versão), e roda no `pdm-bia-505511` com modelos re-treinados e registrados lá.

**Architecture:** `modelo/api.py` (955 linhas) é dividido em `modelo/api/` (config, features, modelos, predição, rotas, main). O caminho push (`/pubsub`, MERGE no BigQuery, publicação em `predicoes`) sai: a partir do plano 2 quem chama a API e grava o resultado é o Dataflow. Cada versão no Registry passa a levar um `features.json` com as features que usa. Brasileirão e Premier são re-treinados e registrados no Vertex AI do `pdm-bia-505511`, e a API é publicada lá, privada.

**Tech Stack:** Python 3.12, FastAPI, scikit-learn 1.6.1, Vertex AI Model Registry (REST), Cloud Storage, Cloud Run, pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-11-11-pipeline-integrado-design.md` (§7.2, §7.3 e §7.4; este é o 1º de uma série de planos, o item 1 da §8)

## Global Constraints

- Projeto GCP: `pdm-bia-505511`. Todo `gcloud`/`bq` leva `--project=pdm-bia-505511`/`--project_id=pdm-bia-505511`; clientes Python rodam com `GOOGLE_CLOUD_QUOTA_PROJECT=pdm-bia-505511` (o projeto padrão local é outro).
- `scikit-learn==1.6.1` fica fixo (`modelo/requirements.txt`): o `.joblib` precisa carregar na API.
- Regra de promoção inalterada: bate sempre mandante (acurácia), frequências (log loss) e o campeão atual (log loss) no `TEST`; empate não promove; alias `campeao`.
- Nenhum modelo reprovado é servido: sem alias `campeao` = sem predição (`sem_campeao`).
- Nomes, mensagens e docs em português; docs do repositório escritas como projeto, sem referência a disciplina/entrega.
- `make lint` e `uv run pytest` verdes ao fim de cada task.
- Nenhum arquivo de `modelo/api/` passa de 300 linhas.

## Review Focus

1. Versão cujo `features.json` cita coluna que não existe na gold → `503` com motivo `features_ausentes`, nunca NaN silencioso (teste na Task 3).
2. Lote com resultados mistos (ok, `fora_da_gold`, `sem_campeao`) → HTTP 200, um resultado por pedido na mesma ordem, cada um com seu status (teste na Task 5).
3. Alias `campeao` removido no Registry com o modelo já carregado → a API para de servir aquela liga na próxima conferência (teste na Task 4).
4. Registry fora do ar sem modelo carregado → `503 indisponivel`, não `409 sem_campeao`: o Dataflow só re-tenta o primeiro (teste na Task 4).
5. Evento de competição sem entrada em `LIGAS` (ex.: `ELC`) → `409 sem_campeao`, não `404` (teste na Task 5).

---

### Task 1: Tirar o caminho push da API

O Dataflow passa a ser o único caminho (spec §7.3). Remover antes de dividir, para não mover código morto.

**Files:**
- Modify: `modelo/api.py`
- Modify: `tests/test_modelo_api.py`

**Interfaces:**
- Produces: `criar_app(cfg=None, *, features=None, modelos=None, relogio=agora, aquecer=False) -> FastAPI` (sem `publicar`, `verificar`, `avaliacao`); `Config` sem `topico`, `push_sa`, `push_audience`, `verificar_token`, `tabela_avaliacao`; `Pedido` sem `publicar`.

- [ ] **Step 1: Ajustar os testes ao contrato sem push**
  - Apagar: todos os `test_pubsub_*`, `test_predict_sem_publicar`, `test_predict_falha_ao_publicar_ainda_responde`, `test_agendada_*`, `test_encerrada_*`, `test_falha_na_tabela_*`, `test_health_mostra_a_tabela`, `test_resultado_real`, `test_merge_*`, e as fixtures `publicadas`, `com_tabela` e `envelope`.
  - Guardar o corpo de `test_pubsub_replay_acha_a_partida_pelo_confronto`: ele volta na Task 5, via `/predict`.
  - Renomear `test_predict_devolve_e_publica_o_formato_do_contrato` → `test_predict_devolve_o_formato_do_contrato`; tirar a asserção sobre `publicadas` e sobre `X-Publicada`.
  - Fixture `cliente`: `api.criar_app(api.Config(), features=..., modelos=..., relogio=lambda: AGORA)`.
  - Novo teste:

```python
def test_rota_pubsub_nao_existe_mais(cliente):
    assert cliente.post("/pubsub", json={}).status_code == 404
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_modelo_api.py -q`
Expected: FAIL (`criar_app` ainda não aceita a chamada sem `verificar_token=False`, ou `/pubsub` responde 401).

- [ ] **Step 3: Remover de `modelo/api.py`**
  - `publicador`, `verificador`, `Recentes`, `ler_evento`, `resultado_real`, `_instante`, `Avaliacao`, `AGENDADA`, a rota `/pubsub` e `processar`.
  - Os parâmetros e campos listados em Interfaces.
  - `predicoes_vs_real` do `/health` e o header `X-Publicada`.
  - Os imports que sobrarem (`base64`, `OrderedDict`, `ClassVar`, `Request`).
  - Docstring do módulo: as rotas agora são `/predict` e `/health`.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_modelo_api.py tests/test_modelo_treino.py -q && make lint`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add modelo/api.py tests/test_modelo_api.py
git commit -m "refactor(modelo): tira o caminho push da API; o Dataflow passa a chamar o /predict"
```

---

### Task 2: Dividir a API em pacote

Só move código: nenhuma mudança de comportamento.

**Files:**
- Create: `modelo/api/__init__.py`, `modelo/api/config.py`, `modelo/api/features.py`, `modelo/api/modelos.py`, `modelo/api/predicao.py`, `modelo/api/rotas.py`, `modelo/api/main.py`
- Delete: `modelo/api.py`
- Modify: `modelo/Dockerfile`, `tests/test_modelo_api.py`, `tests/test_modelo_treino.py`

**Interfaces:**
- Produces, conteúdo de cada módulo:

  | módulo | conteúdo |
  |---|---|
  | `config.py` | `RAIZ` (= `Path(__file__).resolve().parents[2]`), `PIPELINE`, `DADOS`, `CLASSES`, `FEATURES`, `COLUNAS`, `Liga`, `LIGAS`, `Config`, `ambiente`, `agora` |
  | `features.py` | `baixar_publico`, `ler_parquet`, `Features` |
  | `modelos.py` | `SemModeloError`, `Modelo`, `Fonte`, `Registry`, `PastaLocal`, `validar`, `Modelos`, `fonte_padrao` |
  | `predicao.py` | `vetor`, `probabilidades`, `prediction_id`, `predicao` |
  | `rotas.py` | `Pedido`, `criar_app` |
  | `main.py` | `logging.basicConfig(...)` e `app = criar_app(aquecer=True)` |
  | `__init__.py` | reexporta todos os nomes acima com `__all__` explícito, sem criar o `app` |

  `import api` continua dando `api.LIGAS`, `api.Registry`, `api.vetor` etc., então `modelo/treinar.py` não muda.

- [ ] **Step 1: Trocar o carregamento do módulo nos testes**

Nos dois arquivos de teste, troque `_modulo("api")` por:

```python
sys.path.insert(0, str(MODELO))
import api  # noqa: E402
```

Em `test_modelo_treino.py`, `treinar` continua carregado por `_modulo("treinar")`.

Novo teste em `tests/test_modelo_api.py`:

```python
def test_pacote_nao_cria_app_ao_importar():
    assert not hasattr(api, "app")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_modelo_api.py -q`
Expected: FAIL em `test_pacote_nao_cria_app_ao_importar` (o `api.py` cria `app` na importação).

- [ ] **Step 3: Criar o pacote movendo o código, e apagar `modelo/api.py`**

Os módulos importam entre si de forma relativa (`from .config import ...`). A docstring de `__init__.py` fica com a visão geral que estava no topo do `api.py`.

- [ ] **Step 4: Ajustar a imagem**

Em `modelo/Dockerfile`: `COPY api/ ./api/` e `CMD exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8080}"`.

- [ ] **Step 5: Verificar**

Run: `uv run pytest tests/test_modelo_api.py tests/test_modelo_treino.py -q && make lint && wc -l modelo/api/*.py`
Expected: PASS, e nenhum arquivo acima de 300 linhas.

Run: `cd modelo && uv run --no-project --with-requirements requirements.txt python -c "import api.main; print(api.main.app.title)"`
Expected: `Foota Toota: modelo`

- [ ] **Step 6: Commit**

```bash
git add -A modelo/api modelo/api.py modelo/Dockerfile tests/test_modelo_api.py tests/test_modelo_treino.py
git commit -m "refactor(modelo): divide a API em pacote com módulos por responsabilidade"
```

---

### Task 3: Lista de features por versão e `features_ate`

Spec §7.2 (formato do candidato) e §7.4.

**Files:**
- Modify: `modelo/api/modelos.py`, `modelo/api/predicao.py`, `modelo/api/features.py`, `modelo/api/rotas.py`, `modelo/treinar.py`
- Test: `tests/test_modelo_api.py`, `tests/test_modelo_treino.py`

**Interfaces:**
- Produces:
  - `Modelo(estimador: Any, versao: str, features: tuple[str, ...])`.
  - `Fonte.carregar(uri: str) -> tuple[Any, tuple[str, ...]]`. Lê o `model.joblib` e o `features.json` (uma lista JSON de nomes) do mesmo diretório. Sem `features.json`, usa `FEATURES` (versões antigas).
  - `validar(estimador: Any, features: Sequence[str]) -> Any` confere `n_features_in_ == len(features)`.
  - `vetor(linha: dict, nomes: Sequence[str] = FEATURES) -> list[float]`.
  - `predicao(...)` passa a incluir `"features_ate"`: `linha.get("features_ate")` em ISO 8601 com `Z`, ou `None`.
  - `class FeaturesAusentesError(Exception)`.
  - `Features.colunas: frozenset[str]` são as colunas lidas da gold.
  - `ler(dados: bytes, colunas: list[str] | None)`: com `None`, lê todas as colunas.
  - Em `treinar.py`:
    - `Conjunto` ganha `linhas: list[dict]`;
    - `separar(linhas, nomes=FEATURES)`;
    - `treinar_liga(liga, linhas, atual, features=FEATURES, **busca)`;
    - `modelo_atual(...)` devolve `(versao, estimador, features)`;
    - o campeão é avaliado com as features dele, sobre `teste.linhas`;
    - os arquivos enviados ganham `features.json`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_predicao_usa_as_features_da_versao(cliente, fonte):
    fonte.features = ("home_rest_days", "away_rest_days")
    fonte.estimador.n_features_in_ = 2
    fonte.versao_atual = "4"
    r = cliente.post("/predict", json={"match_id": "fduk_BRA_x"})
    assert r.status_code == 200
    assert fonte.estimador.entradas[-1] == [[9.0, 1.0]]

def test_versao_que_pede_coluna_fora_da_gold_responde_503(cliente, fonte):
    fonte.features = ("home_rest_days", "coluna_que_nao_existe")
    fonte.estimador.n_features_in_ = 2
    fonte.versao_atual = "5"
    r = cliente.post("/predict", json={"match_id": "fdorg_555047"})
    assert r.status_code == 503
    assert r.json()["detail"]["motivo"] == "features_ausentes"

def test_predicao_traz_features_ate(fonte):
    ...  # gold com features_ate = datetime(2026, 10, 12, 21, 0, tzinfo=UTC)
    assert r.json()["features_ate"] == "2026-10-12T21:00:00Z"

def test_predicao_sem_features_ate_na_gold_devolve_none(cliente):
    assert cliente.post("/predict", json={"match_id": "fdorg_555047"}).json()["features_ate"] is None
```

- `FonteFalsa.carregar` devolve `(self.estimador, self.features)`, com padrão `api.FEATURES`.
- `CAMPOS` ganha `"features_ate"`.
- Em `test_modelo_treino.py`:
  - `test_treino_grava_features_json`: os arquivos enviados contêm `features.json == json.dumps(list(api.FEATURES))`.
  - `test_campeao_e_avaliado_com_as_features_dele`: o campeão com 2 features recebe vetores de tamanho 2.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_modelo_api.py tests/test_modelo_treino.py -q`
Expected: FAIL nos testes novos.

- [ ] **Step 3: Implementar as interfaces acima**

Em `rotas.py`, antes de prever:
- se `set(modelo.features) - loja.colunas` não for vazio, levantar `FeaturesAusentesError`, que vira `503 {"motivo": "features_ausentes"}`;
- com features diretas, a validação de `sobra` usa `modelo.features`.

`Features` deixa de usar `COLUNAS` (apagar a constante se ninguém mais usar). `treinar.py` lê a gold com `colunas=None`.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_modelo_api.py tests/test_modelo_treino.py -q && make lint`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add modelo tests
git commit -m "feat(modelo): cada versão leva sua lista de features; predição devolve features_ate"
```

---

### Task 4: Sem campeão não há predição, e erros com motivo

Spec §7.2 (competição sem campeão) e §7.3 (o Dataflow re-tenta só falha transitória).

**Files:**
- Modify: `modelo/api/modelos.py`, `modelo/api/rotas.py`
- Test: `tests/test_modelo_api.py`

**Interfaces:**
- Produces:
  - `class SemCampeaoError(SemModeloError)`. `Registry.versao` a levanta quando o modelo não existe ou não tem o alias `campeao`; o fallback para o alias `default` sai. `PastaLocal.versao` também a levanta quando falta o arquivo.
  - `Modelos.obter`:
    - `SemCampeaoError` descarta a versão carregada e propaga;
    - qualquer outro erro mantém a versão carregada, como hoje;
    - sem versão carregada, propaga `SemModeloError`.
  - Erros das rotas: `HTTPException(status, {"motivo": <str>, "mensagem": <str>})`:

    | status | motivo | quando |
    |---|---|---|
    | 404 | `fora_da_gold` | partida não está na gold |
    | 409 | `sem_campeao` | liga sem campeão ou competição sem entrada em `LIGAS` |
    | 503 | `indisponivel` | gold ou Registry fora do ar |
    | 503 | `features_ausentes` | ver Task 3 |
    | 422 | — | pedido inválido; formato do FastAPI, sem mudança |

  - `/health`, por liga: `"versao": None` e `"motivo": "sem_campeao"` quando for o caso.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_liga_sem_campeao_responde_409(cliente, fonte):
    fonte.falhar = api.SemCampeaoError("sem alias campeao")
    r = cliente.post("/predict", json={"match_id": "fdorg_555047"})
    assert r.status_code == 409
    assert r.json()["detail"]["motivo"] == "sem_campeao"

def test_alias_removido_para_de_servir(fonte):
    relogio = Relogio()
    modelos = api.Modelos(fonte, 600.0, relogio=relogio)
    modelos.obter(BSA)
    fonte.falhar = api.SemCampeaoError("alias removido")
    relogio.t = 601
    with pytest.raises(api.SemCampeaoError):
        modelos.obter(BSA)

def test_registry_fora_sem_modelo_carregado_responde_503(cliente, fonte):
    fonte.falhar = RuntimeError("timeout")
    r = cliente.post("/predict", json={"match_id": "fdorg_555047"})
    assert r.status_code == 503
    assert r.json()["detail"]["motivo"] == "indisponivel"

def test_partida_fora_da_gold_responde_404_com_motivo(cliente):
    r = cliente.post("/predict", json={"match_id": "nao_existe"})
    assert r.json()["detail"]["motivo"] == "fora_da_gold"

def test_registry_sem_alias_campeao_nao_cai_no_default():
    ...  # sessão falsa: GET @campeao -> 404, GET @default -> 200
    with pytest.raises(api.SemCampeaoError):
        registry.versao("boosted_tree_epl")
```

Apagar `test_predict_liga_sem_modelo_responde_503`, que foi substituído pelos dois primeiros testes acima.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_modelo_api.py -q`
Expected: FAIL nos testes novos.

- [ ] **Step 3: Implementar**

As rotas montam os erros a partir de uma exceção interna `Falha(status: int, motivo: str, mensagem: str)`, convertida em `HTTPException` num ponto só. A Task 5 reaproveita essa exceção no lote.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_modelo_api.py tests/test_modelo_treino.py -q && make lint`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add modelo/api tests/test_modelo_api.py
git commit -m "feat(modelo): sem campeão não há predição; erros da API com motivo"
```

---

### Task 5: Pedido com contexto do evento e `POST /predict/lote`

Spec §7.3 (idempotência, eficiência).

**Files:**
- Modify: `modelo/api/rotas.py`, `modelo/api/config.py`
- Test: `tests/test_modelo_api.py`

**Interfaces:**
- Produces:
  - `Pedido` ganha, todos opcionais:
    - `event_id: str | None`: com ele, o `prediction_id` é determinístico (`prediction_id(event_id, ...)`); sem ele, é um UUID novo, como hoje;
    - `competition: str | None`: código do Football-Data.org, resolvido via `Liga.competicao`;
    - `season: int | None`, `home_team_id: str | None`, `away_team_id: str | None`: para achar a partida pelo confronto, como o `/pubsub` fazia.
  - `league_id` vence `competition` quando os dois vierem.
  - `def prever(pedido: Pedido) -> dict` (fechamento dentro de `criar_app`) devolve a predição ou levanta `Falha`. As duas rotas usam essa função.
  - `POST /predict/lote`:
    - corpo `{"pedidos": [Pedido, ...]}`, com 1 a 100 itens (mais que isso → 422);
    - resposta sempre 200: `{"resultados": [{"match_id", "event_id", "status": int, "predicao": dict | None, "motivo": str | None}]}`, na ordem dos pedidos, com `status` igual ao que o `/predict` daria.

- [ ] **Step 1: Escrever os testes que falham**
  - `test_predict_acha_a_partida_pelo_confronto`: o corpo guardado na Task 1, enviando `{"match_id": "fdorg_555047", "competition": "BSA", "season": 2026, "home_team_id": "4364", "away_team_id": "6684"}` para uma gold onde a partida só existe com outro id.
  - `test_prediction_id_estavel_com_event_id`: dois POSTs com o mesmo `event_id` → mesmo `prediction_id`.
  - `test_competicao_sem_liga_responde_409`: `{"match_id": "x", "competition": "ELC"}` → 409, `sem_campeao`.
  - `test_lote_com_resultados_mistos`: três pedidos (ok, `fora_da_gold`, `competition: "ELC"`) → HTTP 200, `status` `[200, 404, 409]` na ordem, `predicao` só no primeiro.
  - `test_lote_acima_de_100_responde_422`.
  - `test_lote_le_a_gold_uma_vez_por_liga`: 50 pedidos BSA → `Loja.leituras == 1`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_modelo_api.py -q`
Expected: FAIL nos testes novos.

- [ ] **Step 3: Implementar as interfaces acima**

O lote roda `prever` em sequência. O modelo e a gold já ficam em cache nas lojas, então não há trabalho repetido.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_modelo_api.py tests/test_modelo_treino.py -q && make lint`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add modelo/api tests/test_modelo_api.py
git commit -m "feat(modelo): /predict aceita o contexto do evento; novo /predict/lote"
```

---

### Task 6: Treinar, registrar e publicar no `pdm-bia-505511`

**Files:**
- Modify: `modelo/deploy_api.sh`, `modelo/requirements.txt`, `README.md` (seção Modelo), `docs/arquitetura/contratos.md` (seção 4, rotas da API)
- Delete: `modelo/sql/` (a avaliação passa para a gold no plano 2)

**Interfaces:**
- Produces, para o plano 2:
  - o serviço Cloud Run `modelo-api` em `pdm-bia-505511`, `us-central1`, **privado** (`--no-allow-unauthenticated`);
  - a service account `modelo-api@pdm-bia-505511.iam.gserviceaccount.com`;
  - os modelos `boosted_tree_brasileirao` e `boosted_tree_epl` no Registry do `pdm-bia-505511`, com o alias `campeao`;
  - o bucket `gs://pdm-bia-505511-modelos`.

- [ ] **Step 1: Reescrever o `deploy_api.sh`**
  - `MODELO_PROJECT_ID` com padrão `pdm-bia-505511`; `MODELO_PUBLICO` com padrão `0`.
  - Sai tudo que for de push, tópico, `modelo/sql` e `GRANT` no dataset.
  - Papéis da SA: `roles/aiplatform.viewer` no projeto e `roles/storage.objectViewer` no bucket `pdm-bia-505511-modelos`. Sai o `bigquery.jobUser`.
  - Variáveis do serviço: `MODELO_PROJECT_ID`, `MODELO_REGIAO`.
  - O rodapé passa a imprimir a URL e um `curl` com `Authorization: Bearer $(gcloud auth print-identity-token)`.

- [ ] **Step 2: Limpar as dependências**

Tire `google-cloud-pubsub` e `google-cloud-bigquery` de `modelo/requirements.txt` se `grep -rn "pubsub\|bigquery" modelo/api modelo/treinar.py` não achar uso. Apague `modelo/sql/`.

Run: `make lint && uv run pytest -q`
Expected: PASS

- [ ] **Step 3: Treinar e registrar no projeto**

```bash
export GOOGLE_CLOUD_QUOTA_PROJECT=pdm-bia-505511
MODELO_PROJECT_ID=pdm-bia-505511 MODELOS_BUCKET=pdm-bia-505511-modelos \
  uv run --no-project --with-requirements modelo/requirements-treino.txt \
  python modelo/treinar.py
```

Expected: para cada liga, `registrado: <modelo> versão 1 (...); alias campeao: nenhuma -> 1`. Sem campeão anterior, a comparação é só com os dois baselines.

Uma liga reprovada fica sem campeão. Isso é aceito, mas anote para o relatório final.

- [ ] **Step 4: Publicar e verificar**

Run: `modelo/deploy_api.sh`
Expected: termina com `pronto: https://modelo-api-...run.app`

Run: `curl -s -o /dev/null -w '%{http_code}' $URL/health`
Expected: `403` (serviço privado)

Run: `curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" $URL/health`
Expected: as duas ligas com `versao` não nula.

Run:

```bash
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H 'Content-Type: application/json' \
  -d '{"pedidos":[{"match_id":"fdorg_555095","competition":"BSA"},{"match_id":"x","competition":"ELC"}]}' \
  $URL/predict/lote
```

Expected: `status` `[200, 409]`. O primeiro resultado traz `features_ate` (pode ser `null` até a gold ganhar a coluna) e `model_version` `"1"`.

- [ ] **Step 5: Atualizar a documentação**
  - `contratos.md`, seção 4:
    - rotas `/predict`, `/predict/lote` e `/health`;
    - a tabela de status e motivo da Task 4;
    - os campos do `Pedido`;
    - "chamada pelo Dataflow com ID token".
  - README, seção Modelo:
    - um projeto só;
    - API privada;
    - pacote `modelo/api/`;
    - `features.json` por versão.

  Sem mencionar a disciplina.

- [ ] **Step 6: Commit**

```bash
git add -A modelo README.md docs/arquitetura/contratos.md
git commit -m "feat(modelo): API e Registry no pdm-bia-505511, API privada"
```
