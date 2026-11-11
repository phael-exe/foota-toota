# Dataflow chamando a API do modelo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O Dataflow prevê cada partida agendada chamando `POST /predict/lote` no Cloud Run e grava o evento já com a predição em `stream.partidas`; a gold lê as predições só dali.

**Architecture:** As funções de inferência (montar o pedido, chamar com retry, anexar a predição, montar a falha) ficam em `streaming/pipeline.py`, sem importar o Beam, como a limpeza já faz. Um `DoFn` com sessão autenticada por ID token chama a API em lotes de até 100 eventos. O evento sempre segue para `stream.partidas` (com ou sem predição); o que não virou predição vai também para `stream.predicoes_falhas` com o motivo. O push `eventos-api` sai.

**Tech Stack:** Apache Beam 2.77 (Dataflow, Python 3.12), google-auth (ID token), requests, BigQuery, pytest.

**Spec:** `docs/superpowers/specs/2026-11-11-pipeline-integrado-design.md` (§7.3, §7.4, §9)

## Global Constraints

- Tudo no projeto `pdm-bia-505511`; `GOOGLE_CLOUD_QUOTA_PROJECT=pdm-bia-505511` em todo comando local.
- Só eventos de jogo **ainda não iniciado** (`status = 'scheduled'` depois da limpeza) chamam a API.
- Retry com backoff exponencial só para transitórios: timeout, erro de conexão, 429 e 5xx (no lote e por item). 4xx não re-tenta.
- Evento que não vira predição vai para a tabela de falhas com o motivo; nunca some em silêncio, e o evento em si continua em `stream.partidas`.
- Sessão HTTP reaproveitada por worker; lote de no máximo 100 (`LOTE_MAXIMO` da API).
- `prediction_id` vem da API (determinístico por evento + modelo + versão); a gold descarta repetidos por ele.
- A gold lê as predições de um lugar só: `stream.partidas`.
- Docs do repositório sem linguagem de disciplina (nada de "Trabalho", "T2", "trabalho final").
- Nomes em português, seguindo o vocabulário atual (`stream.*`, `gold.*`); colunas já existentes em inglês continuam.

## Decisões deste plano (o que a spec deixou para o construtor)

- **Evento enriquecido:** colunas novas e anuláveis em `stream.partidas` (`prediction_id`, `model_name`, `model_version`, `prob_home`, `prob_draw`, `prob_away`, `predicted_outcome`, `predicted_at`, `features_ate`). `stream.predicoes` fica como histórico antigo, sem leitor.
- **Gold:** nova view `gold.predicoes` (uma linha por `prediction_id`, formato do contrato + `kickoff_utc`, `mode`, `features_ate`, `prevista_antes_do_jogo`, `features_antes_do_jogo`); `gold.predicoes_avaliadas` passa a ler dela; a exportação pública `gold/predictions.parquet` também.
- **Tamanho do lote:** `beam.BatchElements(min_batch_size=1, max_batch_size=100)`.
- **Tentativas:** 4 no total, espera 1 s, 2 s, 4 s. Timeout por requisição `(5, 60)` (conexão, leitura): o cold start da API é ~24 s.
- **Conta dos workers:** a padrão do Compute (`<número>-compute@developer.gserviceaccount.com`), que ganha `roles/run.invoker` só no serviço `modelo-api`. O `dataflow.sh iniciar` dá a permissão e passa a URL da API.
- **O tópico `predicoes` não recebe mais nada.** Os pushes que dependem dele (`predicoes-plataforma`) ficam sem novidades; a plataforma lê `gold/predictions.parquet`, que continua no mesmo formato.

## Review Focus

1. Primeiro lote depois de a API escalar a zero: o timeout de leitura de 60 s cobre o cold start; se estourar, re-tenta e não perde o evento.
2. Resposta 200 malformada (sem `resultados`, ou com tamanho diferente do lote): cada evento vai para falhas com `resposta_invalida`, e a linha da partida é gravada mesmo assim.
3. Replay com `match_id` `fdorg_*` que a gold guarda com outro id: o pedido leva `season`, `home_team_id`, `away_team_id` e `competition`, para a API achar pelo confronto.
4. Pub/Sub reentregando o mesmo evento: duas linhas em `stream.partidas` com o mesmo `prediction_id`; `gold.predicoes` mostra uma.
5. 401/403 (permissão que faltou): não re-tenta, falha com `nao_autorizado`, e a partida chega em `stream.partidas` sem predição.

---

### Task 1: Inferência sem Beam em `streaming/pipeline.py`

**Files:**
- Modify: `streaming/pipeline.py` (seção nova `# --- inferência` antes de `def run`)
- Test: `tests/test_streaming.py` (seção nova `# --- inferência`)

**Interfaces:**
- Produces:
  - `TENTATIVAS = 4`, `ESPERA_S = 1.0`, `TIMEOUT_S = (5, 60)`, `LOTE = 100`
  - `COMPETICOES: dict[str, str]` — inverso de `LIGAS` (`"epl" -> "PL"`)
  - `precisa_predicao(linha: dict) -> bool` — `linha["status"] == "scheduled"`
  - `pedido(linha: dict) -> dict` — `{match_id, event_id, competition, season, home_team_id, away_team_id}` a partir da linha limpa
  - `enriquecer(linha: dict, predicao: dict) -> dict` — cópia da linha com as 9 colunas de predição; `features_ate` e `predicted_at` normalizados com `_instante` (None fica None)
  - `falha(linha: dict, status: int | None, motivo: str, tentativas: int, processado_em: str) -> dict` — linha de `stream.predicoes_falhas`: `{event_id, match_id, league_id, status, motivo, tentativas, processed_at}`
  - `Enviar = Callable[[list[dict]], tuple[int, dict | None]]` — status HTTP e corpo JSON; status `0` para timeout/conexão, com corpo `{"motivo": "timeout" | "conexao"}`
  - `prever_lote(linhas: list[dict], enviar: Enviar, processado_em: str, *, tentativas: int = TENTATIVAS, espera_s: float = ESPERA_S, dormir: Callable[[float], None] = time.sleep) -> tuple[list[dict], list[dict]]` — (todas as linhas, cada uma uma vez, enriquecidas quando previstas; linhas de falha)
  - `enviar_http(sessao: Any, url: str, timeout=TIMEOUT_S) -> Enviar` — POST `{url}/predict/lote` com `{"pedidos": [...]}`

Regras de `prever_lote` (o algoritmo que a assinatura não determina):
- Rodada a rodada, manda só os pendentes. Lote inteiro com status 0, 429 ou ≥500 → todos pendentes de novo. Lote 200 → cada item: 200 vira predição; 429/500/503 fica pendente; outro status vira falha com o `motivo` do item.
- Lote com outro status (401/403 → motivo `nao_autorizado`; demais 4xx → `http_<status>`) → todos viram falha, sem nova tentativa.
- Lote 200 sem `resultados` lista do mesmo tamanho → todos viram falha `resposta_invalida`, sem nova tentativa.
- Entre rodadas, `dormir(espera_s * 2**(rodada-1))`. Esgotadas as tentativas, os pendentes viram falha com o último status e motivo (`indisponivel`, `erro_interno`, `timeout`, `conexao`, `http_<status>`), `tentativas = tentativas`.
- A ordem da saída de linhas é a da entrada.

- [ ] **Step 1: Escrever os testes que falham**

```python
# --- inferência -------------------------------------------------------------


def linha_agendada(**campos):
    _, linha = pipeline.limpar(
        mensagem(status="TIMED", score_home=None, score_away=None), AGORA
    )
    return {**linha, **campos}


def predicao_api(event_id="e1", **campos):
    return {
        "prediction_id": "p-" + event_id,
        "event_id": event_id,
        "match_id": "fdorg_555023",
        "league_id": "brasileirao_serie_a",
        "model_name": "boosted_tree_brasileirao",
        "model_version": "1",
        "prob_home": 0.5,
        "prob_draw": 0.3,
        "prob_away": 0.2,
        "predicted_outcome": "home",
        "predicted_at": "2026-10-16T12:00:01Z",
        "features_ate": "2026-10-01T00:00:00Z",
        **campos,
    }


def item(status, ev, predicao=None, motivo=None):
    return {
        "match_id": "fdorg_555023",
        "event_id": ev,
        "status": status,
        "predicao": predicao,
        "motivo": motivo,
    }


class Api:
    """Responde em ordem as respostas dadas e guarda os pedidos."""

    def __init__(self, *respostas):
        self.respostas, self.chamadas = list(respostas), []

    def __call__(self, pedidos):
        self.chamadas.append(pedidos)
        return self.respostas.pop(0)


def test_so_partida_agendada_pede_predicao():
    assert pipeline.precisa_predicao(linha_agendada())
    assert not pipeline.precisa_predicao(linha_agendada(status="finished"))
    assert not pipeline.precisa_predicao(linha_agendada(status="in_play"))


def test_pedido_leva_o_confronto_e_o_codigo_da_competicao():
    p = pipeline.pedido(linha_agendada(event_id="e1"))
    assert p == {
        "match_id": "fdorg_555023",
        "event_id": "e1",
        "competition": "BSA",
        "season": 2026,
        "home_team_id": "1771",
        "away_team_id": "1776",
    }


def test_lote_previsto_volta_enriquecido_e_sem_falha():
    linhas = [linha_agendada(event_id="e1"), linha_agendada(event_id="e2")]
    api = Api(
        (
            200,
            {
                "resultados": [
                    item(200, "e1", predicao_api("e1")),
                    item(200, "e2", predicao_api("e2")),
                ]
            },
        )
    )
    saida, falhas = pipeline.prever_lote(
        linhas, api, AGORA, dormir=lambda s: None
    )
    assert falhas == []
    assert [l["prediction_id"] for l in saida] == ["p-e1", "p-e2"]
    assert saida[0]["predicted_outcome"] == "home"
    assert saida[0]["features_ate"] == "2026-10-01T00:00:00+00:00"
    assert saida[0]["status"] == "scheduled"  # o resto da linha continua


def test_4xx_de_um_item_vira_falha_sem_nova_tentativa():
    linhas = [linha_agendada(event_id="e1"), linha_agendada(event_id="e2")]
    api = Api(
        (
            200,
            {
                "resultados": [
                    item(200, "e1", predicao_api("e1")),
                    item(409, "e2", motivo="sem_campeao"),
                ]
            },
        )
    )
    saida, falhas = pipeline.prever_lote(
        linhas, api, AGORA, dormir=lambda s: None
    )
    assert len(api.chamadas) == 1
    assert saida[1]["prediction_id"] is None
    assert falhas == [
        {
            "event_id": "e2",
            "match_id": "fdorg_555023",
            "league_id": "brasileirao_serie_a",
            "status": 409,
            "motivo": "sem_campeao",
            "tentativas": 1,
            "processed_at": AGORA,
        }
    ]


def test_item_503_tenta_de_novo_so_ele_com_backoff():
    linhas = [linha_agendada(event_id="e1"), linha_agendada(event_id="e2")]
    esperas = []
    api = Api(
        (
            200,
            {
                "resultados": [
                    item(200, "e1", predicao_api("e1")),
                    item(503, "e2", motivo="indisponivel"),
                ]
            },
        ),
        (200, {"resultados": [item(200, "e2", predicao_api("e2"))]}),
    )
    saida, falhas = pipeline.prever_lote(
        linhas, api, AGORA, dormir=esperas.append
    )
    assert [len(c) for c in api.chamadas] == [2, 1]
    assert api.chamadas[1][0]["event_id"] == "e2"
    assert esperas == [1.0]
    assert falhas == [] and saida[1]["prediction_id"] == "p-e2"


def test_timeout_esgota_as_tentativas_e_vira_falha():
    esperas = []
    api = Api(*[(0, {"motivo": "timeout"})] * 4)
    saida, falhas = pipeline.prever_lote(
        [linha_agendada(event_id="e1")], api, AGORA, dormir=esperas.append
    )
    assert esperas == [1.0, 2.0, 4.0]
    assert saida[0]["prediction_id"] is None
    assert falhas[0]["status"] is None and falhas[0]["motivo"] == "timeout"
    assert falhas[0]["tentativas"] == 4


@pytest.mark.parametrize(
    "status, motivo",
    [(401, "nao_autorizado"), (403, "nao_autorizado"), (422, "http_422")],
)
def test_lote_4xx_falha_tudo_sem_nova_tentativa(status, motivo):
    api = Api((status, None))
    saida, falhas = pipeline.prever_lote(
        [linha_agendada(event_id="e1")], api, AGORA, dormir=lambda s: None
    )
    assert len(api.chamadas) == 1
    assert (
        len(saida) == 1
        and falhas[0]["motivo"] == motivo
        and falhas[0]["status"] == status
    )


@pytest.mark.parametrize("corpo", [None, {}, {"resultados": []}])
def test_resposta_malformada_vira_falha_e_a_linha_segue(corpo):
    api = Api((200, corpo))
    saida, falhas = pipeline.prever_lote(
        [linha_agendada(event_id="e1")], api, AGORA, dormir=lambda s: None
    )
    assert len(api.chamadas) == 1
    assert saida[0]["event_id"] == "e1" and saida[0]["prediction_id"] is None
    assert falhas[0]["motivo"] == "resposta_invalida"


def test_enviar_http_manda_o_lote_e_traduz_timeout():
    import requests

    class Sessao:
        def __init__(self, erro=None):
            self.erro, self.posts = erro, []

        def post(self, url, json, timeout):
            self.posts.append((url, json, timeout))
            if self.erro:
                raise self.erro

            class R:
                status_code = 200

                def json(self):
                    return {"resultados": []}

            return R()

    s = Sessao()
    assert pipeline.enviar_http(s, "https://api")([{"match_id": "m"}]) == (
        200,
        {"resultados": []},
    )
    assert s.posts == [
        ("https://api/predict/lote", {"pedidos": [{"match_id": "m"}]}, (5, 60))
    ]
    assert pipeline.enviar_http(Sessao(requests.Timeout()), "https://api")(
        []
    ) == (0, {"motivo": "timeout"})
    assert pipeline.enviar_http(
        Sessao(requests.ConnectionError()), "https://api"
    )([]) == (0, {"motivo": "conexao"})
```

`enriquecer` em linha sem predição: o teste de 4xx exige que a linha que não foi prevista saia com as 9 colunas presentes e `None` (`saida[1]["prediction_id"] is None`), para o schema do BigQuery ser sempre o mesmo.

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_streaming.py -q -k "predicao or pedido or lote or item or timeout or resposta or enviar"`
Expected: FAIL com `AttributeError: module 'pipeline' has no attribute 'precisa_predicao'` (e similares)

- [ ] **Step 3: Implementar as funções da seção Interfaces em `streaming/pipeline.py`**

`import requests` só dentro de `enviar_http` (a limpeza continua sem dependência). Status do item pode faltar → trate como `resposta_invalida` do item. Colunas de predição numa tupla `COLUNAS_PREDICAO` para `enriquecer` e para a linha sem predição.

- [ ] **Step 4: Rodar e ver passar; suíte inteira e lint**

Run: `uv run pytest -q && make lint`
Expected: todos passam; lint limpo

- [ ] **Step 5: Commit**

```bash
git add streaming/pipeline.py tests/test_streaming.py
git commit -m "feat(streaming): previsão em lote com retry e falhas, sem Beam"
```

---

### Task 2: Ligar a inferência no pipeline e no `dataflow.sh`

**Files:**
- Modify: `streaming/pipeline.py` (`run`: argumento `--api_url`, `DoFn` `Prever`, ramos)
- Modify: `streaming/dataflow.sh` (URL da API, `run.invoker` para a conta dos workers)
- Test: `tests/test_streaming_beam.py` (novo; `pytest.importorskip("apache_beam")`, roda no venv `streaming/.venv`)

**Interfaces:**
- Consumes: tudo da Task 1.
- Produces:
  - `class Prever(beam.DoFn)` construída com `Prever(url: str, enviar_de: Callable[[str], Enviar] | None = None)`; `setup()` cria a sessão com `google.oauth2.id_token.fetch_id_token_credentials(url, Request())` + `AuthorizedSession` (audience = URL do serviço) quando `enviar_de` é None; `process(lote)` chama `prever_lote` e emite linhas no saída principal e falhas em `beam.pvalue.TaggedOutput("falhas", ...)`.
  - `def ramo_predicao(limpas, url, enviar_de=None)` → `(partidas, falhas)` PCollections: separa `precisa_predicao`, `BatchElements(min_batch_size=1, max_batch_size=LOTE)`, `ParDo(Prever).with_outputs("falhas", main="partidas")`, `Flatten` com as linhas que não pedem predição. Sem `url`, devolve `limpas` e uma PCollection vazia (`beam.Create([])`).
  - `run`: `--api_url` opcional (padrão vazio); grava falhas em `{projeto}:{dataset}.predicoes_falhas` com o mesmo `gravar`.
  - `dataflow.sh iniciar`: `api_url` de `gcloud run services describe modelo-api --region=$MODELO_REGIAO --format='value(status.url)'` (`MODELO_REGIAO` padrão `us-central1`); `gcloud run services add-iam-policy-binding modelo-api --member=serviceAccount:<número>-compute@developer.gserviceaccount.com --role=roles/run.invoker`; passa `--api_url`. Se o serviço não existir, avisa e sobe sem predição.

`Prever` precisa ser picklável: a sessão nasce no `setup`, nunca no `__init__`. Defina `Prever` dentro de `run`? Não: no nível do módulo, importando `apache_beam` dentro de uma função fábrica `_classe_prever()` para o módulo continuar importável sem Beam. Um jeito simples: `def ramo_predicao(...)` importa o Beam e define a classe ali; o teste usa `ramo_predicao` com `enviar_de` falso.

- [ ] **Step 1: Escrever o teste que falha**

```python
"""Ramo de predição do pipeline, com o Beam (roda no venv do streaming)."""

import pytest

beam = pytest.importorskip("apache_beam")
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to
from test_streaming import linha_agendada, pipeline, predicao_api, item


def test_ramo_preve_agendadas_e_deixa_as_outras_passarem():
    def enviar_de(url):
        def enviar(pedidos):
            return 200, {
                "resultados": [
                    item(200, p["event_id"], predicao_api(p["event_id"]))
                    if p["event_id"] == "e1"
                    else item(409, p["event_id"], motivo="sem_campeao")
                    for p in pedidos
                ]
            }

        return enviar

    linhas = [
        linha_agendada(event_id="e1"),
        linha_agendada(event_id="e2"),
        linha_agendada(event_id="e3", status="finished"),
    ]
    with TestPipeline() as p:
        partidas, falhas = pipeline.ramo_predicao(
            p | beam.Create(linhas), "https://api", enviar_de
        )
        assert_that(
            partidas
            | "ids" >> beam.Map(lambda l: (l["event_id"], l["prediction_id"])),
            equal_to([("e1", "p-e1"), ("e2", None), ("e3", None)]),
            label="partidas",
        )
        assert_that(
            falhas
            | "motivos" >> beam.Map(lambda f: (f["event_id"], f["motivo"])),
            equal_to([("e2", "sem_campeao")]),
            label="falhas",
        )
```

Atenção: a linha `e3` (encerrada) **não** passa por `enriquecer`; para o schema ficar igual, `ramo_predicao` completa com as colunas de predição em `None` também as linhas que não pedem predição (então `l["prediction_id"]` existe em `e3`).

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd streaming && .venv/bin/python -m pip install -q pytest && .venv/bin/python -m pytest ../tests/test_streaming_beam.py -q -p no:cacheprovider --rootdir=..`
Expected: FAIL com `AttributeError: ... 'ramo_predicao'`. (Se o venv não existir: `uv venv streaming/.venv --python 3.12 --seed && uv pip install --python streaming/.venv/bin/python -r streaming/requirements-pipeline.txt pytest`.)

- [ ] **Step 3: Implementar `ramo_predicao`, `Prever` e o `--api_url` em `run`; atualizar `dataflow.sh`**

- [ ] **Step 4: Rodar e ver passar; suíte normal (sem Beam, o arquivo novo é pulado) e lint**

Run: o comando do Step 2, depois `uv run pytest -q && make lint`
Expected: 1 passed no venv do streaming; suíte normal verde com o teste do Beam `skipped`; lint limpo

- [ ] **Step 5: Commit**

```bash
git add streaming/pipeline.py streaming/dataflow.sh tests/test_streaming_beam.py
git commit -m "feat(streaming): Dataflow chama /predict/lote e grava falhas"
```

---

### Task 3: Tabelas e gold

**Files:**
- Modify: `sql/10_stream/03_create_table_partidas.sql` (as 9 colunas, para instalação nova)
- Create: `sql/10_stream/03a_alter_table_partidas_predicao.sql` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` das 9 colunas, para a tabela que já existe; roda antes das views)
- Create: `sql/10_stream/09_create_table_predicoes_falhas.sql`
- Create: `sql/10_stream/10_create_view_predicoes.sql` (`gold.predicoes`)
- Modify: `sql/10_stream/08_create_view_predicoes_avaliadas.sql` (lê `gold.predicoes`) — renomeie para `11_create_view_predicoes_avaliadas.sql` porque depende da 10
- Modify: `sql/10_stream/05_create_table_predicoes.sql` (só o comentário: histórico, sem novos dados)
- Modify: `scripts/exportar_tabelas_publicas.sh` (extrai `gold.predicoes` com as colunas do contrato)
- Test: `tests/test_sql_stream.py` (novo, sem BigQuery)

Colunas novas em `stream.partidas` (todas anuláveis): `prediction_id STRING, model_name STRING, model_version STRING, prob_home FLOAT64, prob_draw FLOAT64, prob_away FLOAT64, predicted_outcome STRING, predicted_at TIMESTAMP, features_ate TIMESTAMP`.

`stream.predicoes_falhas`: `event_id STRING, match_id STRING NOT NULL, league_id STRING, status INT64, motivo STRING NOT NULL, tentativas INT64 NOT NULL, processed_at TIMESTAMP NOT NULL`; `PARTITION BY DATE(processed_at)`; `CREATE TABLE IF NOT EXISTS`.

`gold.predicoes`: de `stream.partidas` onde `prediction_id IS NOT NULL`, uma linha por `prediction_id` (`QUALIFY ROW_NUMBER() OVER (PARTITION BY prediction_id ORDER BY processed_at) = 1`), colunas do contrato (`prediction_id, event_id, match_id, league_id, model_name, model_version, prob_home, prob_draw, prob_away, predicted_outcome, predicted_at`) + `kickoff_utc, mode, features_ate`, `predicted_at < kickoff_utc AS prevista_antes_do_jogo`, `features_ate < kickoff_utc AS features_antes_do_jogo`.

`gold.predicoes_avaliadas`: mesma lógica de resultado de hoje, `FROM gold.predicoes p`.

- [ ] **Step 1: Escrever os testes que falham**

```python
"""SQL do stream: as colunas que o pipeline grava existem nas tabelas."""

import importlib.util, re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SQL = RAIZ / "sql" / "10_stream"
spec = importlib.util.spec_from_file_location(
    "pipeline_sql", RAIZ / "streaming" / "pipeline.py"
)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def colunas(arquivo):
    texto = (SQL / arquivo).read_text()
    return set(
        re.findall(
            r"^\s+(\w+)\s+(?:STRING|INT64|FLOAT64|TIMESTAMP)", texto, re.M
        )
    )


def test_partidas_tem_as_colunas_de_predicao():
    assert set(pipeline.COLUNAS_PREDICAO) <= colunas(
        "03_create_table_partidas.sql"
    )


def test_alter_acrescenta_as_mesmas_colunas():
    texto = (SQL / "03a_alter_table_partidas_predicao.sql").read_text()
    achadas = set(re.findall(r"ADD COLUMN IF NOT EXISTS (\w+)", texto))
    assert achadas == set(pipeline.COLUNAS_PREDICAO)


def test_falhas_tem_as_colunas_que_o_pipeline_grava():
    linha = pipeline.falha(
        {"event_id": "e", "match_id": "m", "league_id": "l"}, 409, "x", 1, "t"
    )
    assert set(linha) == colunas("09_create_table_predicoes_falhas.sql")


def test_views_criadas_depois_do_que_leem():
    nomes = sorted(p.name for p in SQL.glob("*.sql"))
    assert (
        nomes.index("03a_alter_table_partidas_predicao.sql")
        < nomes.index("10_create_view_predicoes.sql")
        < nomes.index("11_create_view_predicoes_avaliadas.sql")
    )
    assert (
        "prevista_antes_do_jogo"
        in (SQL / "10_create_view_predicoes.sql").read_text()
    )
    assert (
        "gold.predicoes`"
        in (SQL / "11_create_view_predicoes_avaliadas.sql").read_text()
    )
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_sql_stream.py -q`
Expected: FAIL (arquivos inexistentes / colunas faltando)

- [ ] **Step 3: Escrever os SQL e ajustar a exportação**

- [ ] **Step 4: Rodar e ver passar; aplicar no BigQuery**

Run: `uv run pytest -q && make lint`, depois
`GOOGLE_CLOUD_QUOTA_PROJECT=pdm-bia-505511 sql/run.sh sql/10_stream/03a_alter_table_partidas_predicao.sql sql/10_stream/09_create_table_predicoes_falhas.sql sql/10_stream/10_create_view_predicoes.sql sql/10_stream/11_create_view_predicoes_avaliadas.sql`
Expected: testes verdes; os quatro scripts sem erro; `bq show --schema pdm-bia-505511:stream.partidas` lista `features_ate`

- [ ] **Step 5: Commit**

```bash
git add sql/10_stream scripts/exportar_tabelas_publicas.sh tests/test_sql_stream.py
git commit -m "feat(stream): predição no evento, tabela de falhas e gold.predicoes"
```

---

### Task 4: Trocar o caminho no GCP e provar ponta a ponta

**Files:**
- Modify: `streaming/infra.sh` (sai o bloco `eventos-api`/`EVENTOS_PUSH_URL` e o bloco `MODELO_SA`; cabeçalho atualizado; cria `predicoes_falhas` via `sql/10_stream`, que já roda)

Operação (projeto `pdm-bia-505511`, sempre com `--project` e `GOOGLE_CLOUD_QUOTA_PROJECT`):

- [ ] **Step 1: Atualizar `infra.sh`** e rodar `bash -n streaming/infra.sh`. Expected: sem saída.
- [ ] **Step 2: Apagar a assinatura push** `gcloud pubsub subscriptions delete eventos-api --project=pdm-bia-505511`. Expected: `Deleted subscription`. (Se não existir, seguir.)
- [ ] **Step 3: Subir o job novo:** `streaming/dataflow.sh parar` (se houver job), esperar sair de `Draining` em `streaming/dataflow.sh status`, depois `streaming/dataflow.sh iniciar`. Expected: job `Running` com o parâmetro `api_url`.
- [ ] **Step 4: Replay curto do Brasileirão:** `uv run python streaming/producer.py replay --rodadas <rodada do TEST> --intervalo 0.2` (escolher a rodada em `sql/04_gold/05_report_split_sets.sql` / gold, fora de TRAIN/EVAL). Expected: eventos publicados.
- [ ] **Step 5: Conferir no BigQuery** (esperar ~2 min):

```sql
SELECT mode, status, COUNTIF(prediction_id IS NOT NULL) AS previstas, COUNT(*) AS eventos
FROM `pdm-bia-505511.stream.partidas`
WHERE DATE(published_at) = CURRENT_DATE() GROUP BY 1, 2;
SELECT motivo, COUNT(*) FROM `pdm-bia-505511.stream.predicoes_falhas`
WHERE DATE(processed_at) = CURRENT_DATE() GROUP BY 1;
SELECT match_id, predicted_at, kickoff_utc, features_ate, prevista_antes_do_jogo, features_antes_do_jogo
FROM `pdm-bia-505511.gold.predicoes` WHERE mode = 'replay' LIMIT 5;
```

Expected: eventos `scheduled` do replay com `previstas > 0`; os que não foram previstos aparecem em falhas com motivo; `features_antes_do_jogo = true` nas linhas do replay.

- [ ] **Step 6: Commit**

```bash
git add streaming/infra.sh
git commit -m "chore(streaming): sai o push eventos-api; o Dataflow é o caminho da predição"
```

---

### Task 5: Documentação

**Files:**
- Modify: `README.md` (diagrama: `DFL -->|"POST /predict/lote"| API`, `DFL --> SFA[("stream.predicoes_falhas")]`, `SPA --> PRE["gold.predicoes"] --> AVA`; tabela de assinaturas sem `eventos-api`; tabela da gold com `gold.predicoes`; consulta de demonstração com `prevista_antes_do_jogo`/`features_antes_do_jogo`; como subir o Dataflow com a API)
- Modify: `docs/arquitetura/contratos.md` (§1 onde fica cada coisa; §2 sem o push para a API; §3 `predicoes` como histórico e o novo caminho em `stream.partidas`/`gold.predicoes`; §4 quem chama é o Dataflow, com ID token; tabela de falhas e motivos do cliente: `timeout`, `conexao`, `nao_autorizado`, `resposta_invalida`, `http_<status>`)

- [ ] **Step 1: Editar os dois arquivos.** Sem "Trabalho"/"T2".
- [ ] **Step 2: Conferir:** `grep -n "eventos-api\|/pubsub\|Trabalho\|T2" README.md docs/arquitetura/contratos.md` → só menções históricas explícitas (ou nenhuma); `make lint` limpo.
- [ ] **Step 3: Commit**

```bash
git add README.md docs/arquitetura/contratos.md
git commit -m "docs: Dataflow chama a API; gold.predicoes e falhas"
```
