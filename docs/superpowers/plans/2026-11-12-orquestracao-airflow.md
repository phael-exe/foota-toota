# Orquestração com Airflow — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um Airflow numa VM do `pdm-bia-505511` dispara o coletor, o replay e o job de notícias, liga e desliga o Dataflow e checa a saúde da API, dos Jobs, do Dataflow e do atraso evento → predição, com alerta por e-mail quando algo falha.

**Architecture:** Airflow 3.3.2 (imagem oficial, sem imagem própria) em `docker compose` com LocalExecutor e Postgres, numa VM e2-standard-2 que roda com uma service account própria. Os DAGs só orquestram: o trabalho é dos Cloud Run Jobs que já existem (`CloudRunExecuteJobOperator`) e da API do Dataflow (cliente `google-cloud-dataflow-client`, porque os operadores de Dataflow do provider exigem o Beam na imagem). A lógica de decisão (validar replay, julgar saúde) fica em funções puras em `orquestracao/dags/foota/`, testadas na suíte normal sem Airflow.

**Tech Stack:** Airflow 3.3.2 (`apache/airflow:3.3.2-python3.12`, provider Google 22.5.0), Postgres 16, Cloud Run Jobs, Dataflow Flex Template, Cloud Logging + Cloud Monitoring (alerta), Compute Engine.

**Spec:** `docs/superpowers/specs/2026-11-11-pipeline-integrado-design.md` (§7.3 cold start, §7.4 replay fora da amostra, §7.5 orquestração, §9 decisões deixadas ao construtor).

## Global Constraints

- Projeto `pdm-bia-505511` explícito em todo `gcloud`/`bq` e em todo cliente Python: o projeto padrão local aponta para outro.
- Nenhuma credencial pessoal dentro de serviço: a VM e as tasks usam a service account `airflow-orquestrador@pdm-bia-505511.iam.gserviceaccount.com`.
- A interface do Airflow não fica pública: escuta só em `127.0.0.1:8080` na VM e é acessada por túnel SSH via IAP; senha aleatória, nunca a padrão.
- Documentação e comentários escritos como projeto, sem referência a disciplina ou entrega; código, nomes e mensagens em português, como o resto do repositório.
- Ruff com `line-length = 80`; `make lint` e `make test` verdes ao fim de cada task.

## Decisões deste plano (o que o spec deixou em aberto)

- **Alerta:** toda task que falha grava uma entrada `ERROR` no log `foota-toota-alertas` do Cloud Logging (callback `on_failure_callback` em todos os DAGs). Uma política do Cloud Monitoring baseada nesse log manda e-mail para `ALERTA_EMAIL` (do `.env`), no máximo um a cada 5 minutos.
- **VM:** `foota-toota-airflow`, e2-standard-2, Debian 12, disco 30 GB, IP externo efêmero (para baixar imagens), nenhuma porta além da 22.
- **Código na VM:** `orquestracao/vm.sh enviar` copia `orquestracao/` por `gcloud compute scp` e roda `docker compose up -d`. Sem `git clone` na VM.
- **Competições ao vivo:** `BSA` e `PL` (as que têm modelo). A lista é uma constante; ampliar é parte do plano das sete ligas.
- **Replay fora da amostra:** o split é por temporada (`gold.match_training_*`), então "rodada fora de TRAIN/EVAL" vira "temporada ≥ a primeira temporada de `TEST` daquela competição", lida do BigQuery na hora do disparo.
- **Cloud Scheduler:** `foota-toota-coletor-5min` e `foota-toota-daily-run` são pausados (não apagados) quando os DAGs equivalentes estão rodando na VM.

## Review Focus

1. **Replay de rodada que não existe** (rodada 99, temporada sem arquivo): o job hoje publica 0 eventos e termina com sucesso, e a demo fica parada sem erro. Espera-se falha visível. → Task 1, `test_replay_sem_partidas_falha`.
2. **API em cold start** (~24 s com `min-instances=0`): o `/health` não pode reprovar só por demorar. → Task 2, `test_api_lenta_mas_ok_nao_e_problema` (timeout de 60 s fica na config, a função julga só status e corpo).
3. **Dataflow desligado de propósito:** com o job drenado, os eventos esperam na assinatura por design; o `saude` não pode acusar atraso nem "Dataflow fora". → Task 2, `test_dataflow_drenado_nao_e_problema` e o atraso só roda com o job `RUNNING`.
4. **Falha antiga do coletor já superada:** uma execução que falhou e depois N execuções boas não devem disparar alerta para sempre; uma falha recente (janela de 30 min) deve, mesmo se a última execução passou. → Task 2, `test_falha_recente_conta_mesmo_com_sucesso_depois` e `test_falha_fora_da_janela_nao_conta`.
5. **Parâmetros do disparo malformados** (`rodadas = "31;rm"`, competição fora da lista): recusar antes de chamar o Job. → Task 2, `test_rodadas_malformadas_sao_recusadas` e `test_competicao_desconhecida_e_recusada`.

---

### Task 1: Replay sem partidas termina com erro

**Files:**
- Modify: `streaming/producer.py` (função `replay`)
- Test: `tests/test_streaming.py`

**Interfaces:**
- Produces: `producer.replay(args, publicar)` levanta `SystemExit` com mensagem `"replay: nenhuma partida em <arquivo> para a temporada <t> e as rodadas <r>"` quando `linha_do_tempo` devolve lista vazia. O Cloud Run Job sai com código ≠ 0, o `CloudRunExecuteJobOperator` falha e o alerta dispara.

- [ ] **Step 1: Escrever o teste que falha**

```python
def test_replay_sem_partidas_falha(tmp_path):
    arquivo = tmp_path / "matches.jsonl"
    arquivo.write_text(json.dumps(partida(rodada=29)) + "\n")
    args = argparse.Namespace(
        arquivo=str(arquivo), temporada=2026, rodadas={99}, intervalo=0
    )
    publicados = []

    with pytest.raises(SystemExit, match="nenhuma partida"):
        producer.replay(args, publicados.extend)

    assert publicados == []
```

- [ ] **Step 2:** `uv run pytest tests/test_streaming.py -k replay_sem_partidas -v` → FAIL (`DID NOT RAISE`).
- [ ] **Step 3:** Em `replay`, logo após `linha_do_tempo`, `sys.exit(...)` com a mensagem acima quando `eventos` está vazio.
- [ ] **Step 4:** `uv run pytest tests/test_streaming.py -v && make lint` → PASS.
- [ ] **Step 5:** Publicar a imagem nova do coletor e provar o override de args que os DAGs vão usar:
  `streaming/deploy_coletor.sh` e depois
  `gcloud run jobs execute foota-toota-coletor --region=us-central1 --project=pdm-bia-505511 --wait --args=python,producer.py,replay,--rodadas,99`
  Expected: execução `failed`, log com `nenhuma partida`.
- [ ] **Step 6: Commit** `fix(streaming): replay sem partidas termina com erro`

---

### Task 2: Regras de decisão da orquestração (sem Airflow)

**Files:**
- Create: `orquestracao/dags/foota/__init__.py` (vazio), `config.py`, `replay.py`, `saude.py`, `alerta.py`, `sql/eventos_sem_predicao.sql`
- Create: `orquestracao/dags/.airflowignore` com a linha `foota/`
- Test: `tests/test_orquestracao.py` (põe `orquestracao/dags` no `sys.path` e importa `foota.*`)

**Interfaces (Produces):**

`foota/config.py` — constantes, com `PROJETO = os.environ.get("GCP_PROJECT_ID", "pdm-bia-505511")`:
`REGIAO = "us-central1"`, `JOB_COLETOR = "foota-toota-coletor"`, `JOB_NOTICIAS = "foota-toota-news-job"`, `JOB_DATAFLOW = "foota-toota-partidas"`, `API = "modelo-api"`, `BUCKET_BRONZE = "foota-toota-505511"`, `BUCKET_STREAM = "foota-toota-505511-stream"`, `TEMPLATE_DATAFLOW = f"gs://{BUCKET_STREAM}/dataflow/templates/partidas.json"`, `COMPETICOES_AO_VIVO = ("BSA", "PL")`, `TABELA_SPLIT = {"BSA": "gold.match_training_brasileirao", "PL": "gold.match_training_epl"}`, `LOG_ALERTAS = "foota-toota-alertas"`, `JANELA_FALHAS = timedelta(minutes=30)`, `ATRASO_MAX_MIN = 10`, `TIMEOUT_HEALTH_S = 60`.

`foota/replay.py`:
- `validar_rodadas(texto: str) -> str` — aceita `^\d+(-\d+)?(,\d+(-\d+)?)*$` (o formato de `producer._rodadas`), devolve sem espaços; senão `ValueError`.
- `consulta_primeira_test(competicao: str) -> str` — `SELECT MIN(season) AS primeira FROM \`{PROJETO}.{TABELA_SPLIT[c]}\` WHERE split_set = 'TEST'`; competição fora de `TABELA_SPLIT` → `ValueError`.
- `checar_fora_da_amostra(competicao: str, temporada: int, primeira_test: int | None) -> None` — `ValueError` se `primeira_test is None` ou `temporada < primeira_test`, com a mensagem `"temporada {t} do {c} está em TRAIN/EVAL do modelo; o TEST começa em {p}"`.
- `argumentos_replay(competicao: str, temporada: int, rodadas: str, intervalo: float) -> list[str]` — `["python", "producer.py", "replay", "--arquivo", f"gs://{BUCKET_BRONZE}/bronze/football_data_org/competition={c}/matches.jsonl", "--temporada", str(t), "--rodadas", validar_rodadas(r), "--intervalo", str(i)]`.
- `overrides(args: list[str]) -> dict` — `{"container_overrides": [{"args": args}]}`.

`foota/saude.py` (cada função devolve a mensagem do problema ou `None`/lista vazia):
- `problema_api(status: int, corpo: dict | None) -> str | None` — `status != 200` → `"/health respondeu {status}"`; `corpo` sem `ligas` ou com `ligas` vazio → `"a API não carregou nenhuma liga"`. Liga com `motivo == "sem_campeao"` não é problema.
- `falhas_de_execucao(execucoes: list[dict], agora: datetime, janela: timedelta) -> list[str]` — cada execução é `{"job": str, "nome": str, "fim": datetime | None, "falhou": bool}`; entra na lista quem `falhou` com `fim >= agora - janela`, como `"{job}: execução {nome} falhou às {fim:%H:%M} UTC"`.
- `estado_dataflow(jobs: list[dict], agora: datetime, janela: timedelta) -> tuple[datetime | None, str | None]` — cada job é `{"estado": str, "inicio": datetime, "fim": datetime | None}`; olha o mais recente por `inicio`. Devolve `(inicio, None)` se `JOB_STATE_RUNNING`; `(None, "o job do Dataflow falhou às ...")` se `JOB_STATE_FAILED` com `fim` na janela; `(None, None)` nos demais (drenado, cancelado, pendente, nenhum job).
- `problema_atraso(pendentes: int, mais_antigo: datetime | None, limite_min: int) -> str | None` — `pendentes > 0` → `"{n} eventos de jogo agendado sem predição há mais de {limite} min (o mais antigo publicado às {hh:mm} UTC)"`.
- `consulta_atraso() -> str` — lê `sql/eventos_sem_predicao.sql` e troca `PROJECT` por `PROJETO` (a convenção de `sql/run.sh`).

`foota/sql/eventos_sem_predicao.sql` — parâmetros `@desde TIMESTAMP` e `@limite_min INT64`; uma linha `(pendentes INT64, mais_antigo TIMESTAMP)`: eventos de `stream.eventos_brutos` com `publish_time >= @desde`, mais velhos que `@limite_min` minutos, `JSON_VALUE(data, '$.status') IN ('SCHEDULED', 'TIMED')`, cujo `event_id` não está em `stream.partidas` nem em `stream.partidas_rejeitadas`.

`foota/alerta.py`:
- `entrada_alerta(dag_id: str, task_id: str, run_id: str, tentativa: int, erro: str) -> dict` — o payload estruturado, com `"mensagem": f"{dag_id}.{task_id} falhou: {erro}"`.
- `registrar_falha(context) -> None` — o `on_failure_callback`: monta a entrada com o `context` e grava com `google.cloud.logging.Client(project=PROJETO).logger(LOG_ALERTAS).log_struct(..., severity="ERROR")`. Erro ao gravar é só logado (o callback não pode derrubar nada).

- [ ] **Step 1: Escrever os testes que falham** em `tests/test_orquestracao.py`:

```python
AGORA = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)
JANELA = timedelta(minutes=30)

def test_argumentos_do_replay_apontam_o_arquivo_da_competicao():
    assert replay.argumentos_replay("PL", 2026, "10-11", 0.5) == [
        "python", "producer.py", "replay",
        "--arquivo", "gs://foota-toota-505511/bronze/football_data_org/competition=PL/matches.jsonl",
        "--temporada", "2026", "--rodadas", "10-11", "--intervalo", "0.5",
    ]

@pytest.mark.parametrize("texto", ["31;rm", "", "a-b", "31-", "-3"])
def test_rodadas_malformadas_sao_recusadas(texto): ...  # ValueError

def test_competicao_desconhecida_e_recusada(): ...  # consulta_primeira_test("XYZ") -> ValueError

def test_temporada_de_treino_e_recusada():
    with pytest.raises(ValueError, match="TEST começa em 2025"):
        replay.checar_fora_da_amostra("BSA", 2024, 2025)
    replay.checar_fora_da_amostra("BSA", 2026, 2025)  # não levanta

def test_sem_test_recusa(): ...  # primeira_test=None -> ValueError

def test_overrides_no_formato_do_cloud_run():
    assert replay.overrides(["a"]) == {"container_overrides": [{"args": ["a"]}]}

def test_api_lenta_mas_ok_nao_e_problema():
    corpo = {"ligas": {"BSA": {"motivo": None}, "PL": {"motivo": "sem_campeao"}}}
    assert saude.problema_api(200, corpo) is None

def test_api_fora_ou_vazia_e_problema():
    assert saude.problema_api(503, None) == "/health respondeu 503"
    assert saude.problema_api(200, {"ligas": {}}) == "a API não carregou nenhuma liga"

def test_falha_recente_conta_mesmo_com_sucesso_depois():
    execucoes = [
        {"job": "coletor", "nome": "c-1", "fim": AGORA - timedelta(minutes=10), "falhou": True},
        {"job": "coletor", "nome": "c-2", "fim": AGORA - timedelta(minutes=5), "falhou": False},
    ]
    assert saude.falhas_de_execucao(execucoes, AGORA, JANELA) == [
        "coletor: execução c-1 falhou às 14:50 UTC"
    ]

def test_falha_fora_da_janela_nao_conta(): ...  # fim = AGORA - 31 min -> []

def test_dataflow_drenado_nao_e_problema():
    jobs = [{"estado": "JOB_STATE_DRAINED", "inicio": AGORA - timedelta(hours=3), "fim": AGORA - timedelta(hours=2)}]
    assert saude.estado_dataflow(jobs, AGORA, JANELA) == (None, None)
    assert saude.estado_dataflow([], AGORA, JANELA) == (None, None)

def test_dataflow_rodando_devolve_o_inicio(): ...  # RUNNING mais recente -> (inicio, None)

def test_dataflow_que_falhou_agora_e_problema(): ...  # FAILED, fim na janela -> (None, "o job do Dataflow falhou às ...")

def test_atraso_so_com_pendentes():
    assert saude.problema_atraso(0, None, 10) is None
    assert saude.problema_atraso(3, AGORA, 10).startswith("3 eventos de jogo agendado")

def test_consulta_de_atraso_usa_o_projeto():
    sql = saude.consulta_atraso()
    assert "PROJECT" not in sql and "`pdm-bia-505511.stream.eventos_brutos`" in sql
    assert "@desde" in sql and "@limite_min" in sql

def test_entrada_do_alerta():
    e = alerta.entrada_alerta("saude", "api_modelo", "r1", 2, "boom")
    assert e["mensagem"] == "saude.api_modelo falhou: boom" and e["tentativa"] == 2
```

- [ ] **Step 2:** `uv run pytest tests/test_orquestracao.py -v` → FAIL (`ModuleNotFoundError: foota`).
- [ ] **Step 3:** Implementar os módulos e o SQL conforme as interfaces.
- [ ] **Step 4:** `uv run pytest tests/test_orquestracao.py -v && make lint` → PASS. Rodar o SQL uma vez no BigQuery (`bq query --project_id=pdm-bia-505511 --use_legacy_sql=false --parameter=desde:TIMESTAMP:2026-11-11T00:00:00Z --parameter=limite_min:INT64:10 < (sed 's/PROJECT/pdm-bia-505511/g' ...)`) → uma linha, sem erro.
- [ ] **Step 5: Commit** `feat(orquestracao): regras de replay e de saúde, sem Airflow`

---

### Task 3: DAGs e stack local do Airflow

**Files:**
- Create: `orquestracao/docker-compose.yaml`, `orquestracao/.env.example`
- Create: `orquestracao/dags/padrao.py` (`PADRAO: dict` = `default_args` comuns: `owner="foota-toota"`, `retries=1`, `retry_delay=timedelta(minutes=1)`, `on_failure_callback=registrar_falha`)
- Create: `orquestracao/dags/coleta_ao_vivo.py`, `coleta_noticias.py`, `disparar_eventos.py`, `saude.py`, `dataflow_liga_desliga.py`
- Create: `orquestracao/tests/test_dags.py` (roda dentro da imagem do Airflow)
- Modify: `pyproject.toml` (ruff `extend-exclude` não; os DAGs passam no ruff como o resto) — só se o ruff reclamar de import de `airflow` não resolvido, o que ele não faz.

**Interfaces:**
- Consumes: tudo de `foota.*` (Task 2).
- Produces: os `dag_id` `coleta_ao_vivo`, `coleta_noticias`, `disparar_eventos`, `saude`, `dataflow_liga_desliga`.

**Compose:** serviços `postgres` (16, volume nomeado), `airflow-init` (`airflow db migrate`, uma vez), `airflow-apiserver` (`api-server`, porta `127.0.0.1:8080:8080`), `airflow-scheduler`, `airflow-dag-processor`. Todos com a imagem `apache/airflow:3.3.2-python3.12` e o mesmo bloco de ambiente:
`AIRFLOW__CORE__EXECUTOR=LocalExecutor`, `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:${POSTGRES_PASSWORD}@postgres/airflow`, `AIRFLOW__CORE__LOAD_EXAMPLES=false`, `AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=true`, `AIRFLOW__CORE__EXECUTION_API_SERVER_URL=http://airflow-apiserver:8080/execution/`, `AIRFLOW__API_AUTH__JWT_SECRET=${JWT_SECRET}`, `AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS=admin:admin`, `AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE=/opt/airflow/senhas/senhas.json`, `AIRFLOW_CONN_GOOGLE_CLOUD_DEFAULT='{"conn_type": "google_cloud_platform", "extra": {"project": "pdm-bia-505511"}}'`, `GCP_PROJECT_ID=pdm-bia-505511`. Volumes: `./dags:/opt/airflow/dags:ro`, `./senhas:/opt/airflow/senhas`. Segredos (`POSTGRES_PASSWORD`, `JWT_SECRET`, a senha do admin) vêm de `orquestracao/.env` e `orquestracao/senhas/senhas.json`, gerados por `vm.sh` (Task 4) e fora do git (`.gitignore`). Localmente, um `docker-compose.local.yaml` de override monta `~/.config/gcloud` em `/home/airflow/.config/gcloud:ro` para o ADC.

**DAGs** (Airflow 3: `from airflow.sdk import dag, task, Param`; `start_date=datetime(2026, 11, 12, tzinfo=UTC)`, `catchup=False`, `default_args=PADRAO`):

| dag_id | schedule | tasks |
|---|---|---|
| `coleta_ao_vivo` | `*/5 * * * *`, `max_active_runs=1` | `CloudRunExecuteJobOperator(job_name=JOB_COLETOR, overrides=overrides(["python", "producer.py", "live", "--uma-vez", "--competicoes", *COMPETICOES_AO_VIVO]), timeout_seconds=300, retries=0)` — a próxima execução já é o retry |
| `coleta_noticias` | `0 6 * * *` | `CloudRunExecuteJobOperator(job_name=JOB_NOTICIAS, timeout_seconds=600)` |
| `disparar_eventos` | `None` | params `competicao` (`Param("BSA", enum=["BSA", "PL"])`), `temporada` (`Param(2026, type="integer")`), `rodadas` (`Param("31", type="string")`), `intervalo` (`Param(0.5, type="number", minimum=0, maximum=10)`). `@task checar_replay(params) -> dict`: valida, lê `consulta_primeira_test` com `BigQueryHook().get_client(project_id=PROJETO)`, `checar_fora_da_amostra`; `ValueError` vira `AirflowFailException` (sem retry). Devolve `overrides(argumentos_replay(...))` → `CloudRunExecuteJobOperator(job_name=JOB_COLETOR, overrides=<XComArg>, verbose=True, retries=0)` (o log do replay aparece na task). |
| `saude` | `*/15 * * * *`, `max_active_runs=1` | `api_modelo`: `GET {url}/health` com ID token (`google.oauth2.id_token.fetch_id_token`, audiência = URL do serviço lida com `run_v2.ServicesClient`), `TIMEOUT_HEALTH_S`; `jobs_cloud_run`: `run_v2.ExecutionsClient.list_executions` de `JOB_COLETOR` e `JOB_NOTICIAS` (falhou = `failed_count > 0`), `falhas_de_execucao`; `dataflow`: `dataflow_v1beta3.JobsV1Beta3Client.list_jobs` filtrado por nome, `estado_dataflow`, devolve o início ou `None`; `atraso_predicao` (depende de `dataflow`): se `None`, termina com `AirflowSkipException`; senão roda `consulta_atraso()` com `@desde = max(inicio, agora - 2 h)` e `@limite_min = ATRASO_MAX_MIN`. Problema → `AirflowFailException(mensagem)` (o callback alerta). `retries=0` em todas. |
| `dataflow_liga_desliga` | `None` | param `acao` (`Param("ligar", enum=["ligar", "desligar"])`); `@task.branch`; **ligar**: `@task iniciar_dataflow` (sai sem nada se já há job ativo; senão `FlexTemplatesServiceClient.launch_flex_template` com `TEMPLATE_DATAFLOW`, parâmetros `api_url` e `subscription`, ambiente `num_workers=1`, `max_workers=1`, `machine_type="n1-standard-1"`, `enable_streaming_engine=True`, `temp_location`, `additional_user_labels={"projeto": "foota-toota"}`) e `@task api_min_instancias(1)`; **desligar**: `@task drenar_dataflow` (`update_job` com `requested_state=JOB_STATE_DRAINED` no job ativo) e `api_min_instancias(0)`. `api_min_instancias(n)` usa `run_v2.ServicesClient.update_service` mudando só `template.scaling.min_instance_count`. |

- [ ] **Step 1: Escrever `orquestracao/tests/test_dags.py`** (pytest dentro da imagem):

```python
def test_dags_carregam_sem_erro():
    bag = DagBag(dag_folder=DAGS, include_examples=False)
    assert bag.import_errors == {}
    assert set(bag.dag_ids) == {
        "coleta_ao_vivo", "coleta_noticias", "disparar_eventos",
        "saude", "dataflow_liga_desliga",
    }

def test_todo_dag_alerta_na_falha():
    for dag in DagBag(dag_folder=DAGS, include_examples=False).dags.values():
        for t in dag.tasks:
            assert t.on_failure_callback, f"{dag.dag_id}.{t.task_id}"

def test_saude_checa_o_atraso_depois_do_dataflow():
    dag = DagBag(dag_folder=DAGS, include_examples=False).dags["saude"]
    assert dag.get_task("atraso_predicao").upstream_task_ids == {"dataflow"}
```

Comando (`orquestracao/testar_dags.sh`): `docker run --rm -v "$PWD/orquestracao:/repo:ro" -e AIRFLOW__CORE__LOAD_EXAMPLES=false --entrypoint bash apache/airflow:3.3.2-python3.12 -c "pip install -q pytest && cd /repo && python -m pytest tests -q -p no:cacheprovider"`.

- [ ] **Step 2:** `orquestracao/testar_dags.sh` → FAIL (nenhum DAG).
- [ ] **Step 3:** Escrever `padrao.py`, os cinco DAGs e o compose.
- [ ] **Step 4:** `orquestracao/testar_dags.sh` → PASS; `make lint test` → PASS.
- [ ] **Step 5: Teste local.** `docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d`; abrir `localhost:8080`; despausar e disparar `disparar_eventos` com `PL`, `2024`, `10` → falha em `checar_replay` com "TRAIN/EVAL" e entrada nova em `gcloud logging read 'logName="projects/pdm-bia-505511/logs/foota-toota-alertas"' --project=pdm-bia-505511 --limit=1`. O `saude` local fica para a VM (o ID token exige service account). `docker compose down`.
- [ ] **Step 6: Commit** `feat(orquestracao): DAGs de coleta, replay, saúde e Dataflow no Airflow`

---

### Task 4: Infra, VM e alerta

**Files:**
- Create: `orquestracao/infra.sh` — idempotente, como `streaming/infra.sh`
- Create: `orquestracao/vm.sh` — `criar | enviar | tunel | senha | ligar | parar | status`
- Create: `orquestracao/instalar_docker.sh` — startup script da VM (Docker Engine + plugin compose do repositório apt da Docker)
- Create: `orquestracao/alerta.json` — política do Cloud Monitoring (condição `conditionMatchedLog` com filtro `logName="projects/pdm-bia-505511/logs/foota-toota-alertas" AND severity>=ERROR`, `alertStrategy.notificationRateLimit.period = "300s"`; o e-mail traz o trecho do log com a mensagem)
- Modify: `.gitignore` (`orquestracao/.env`, `orquestracao/senhas/`)

**`infra.sh` faz:**
1. Habilita `compute`, `iap`, `monitoring`, `logging`, `run`, `dataflow`.
2. Cria a SA `airflow-orquestrador` com: `roles/run.developer`, `roles/dataflow.developer`, `roles/bigquery.jobUser`, `roles/bigquery.dataViewer`, `roles/logging.logWriter`, `roles/monitoring.metricWriter` no projeto; `roles/iam.serviceAccountUser` nas SAs `modelo-api@` e `731571218910-compute@` (para mudar o serviço e lançar o template); `roles/run.invoker` no serviço `modelo-api`; `roles/storage.objectViewer` no bucket `foota-toota-505511-stream`.
3. Firewall `foota-toota-iap-ssh`: `tcp:22` de `35.235.240.0/20`, alvo a tag `airflow`.
4. Se `ALERTA_EMAIL` está no `.env`: cria (ou reaproveita, pelo `displayName`) o canal de e-mail e a política de `alerta.json` apontando para ele. Sem `ALERTA_EMAIL`, avisa e pula: as falhas continuam no Cloud Logging e na interface do Airflow.

**`vm.sh`:**
- `criar`: `gcloud compute instances create foota-toota-airflow --zone=us-central1-a --machine-type=e2-standard-2 --image-family=debian-12 --image-project=debian-cloud --boot-disk-size=30GB --service-account=airflow-orquestrador@... --scopes=cloud-platform --tags=airflow --metadata-from-file=startup-script=orquestracao/instalar_docker.sh --labels=projeto=foota-toota`.
- `enviar`: gera `orquestracao/.env` e `senhas/senhas.json` se não existem (`openssl rand -hex 24`), copia `orquestracao/` para `~/orquestracao` por `gcloud compute scp --recurse --tunnel-through-iap`, roda `docker compose up -d --remove-orphans` e despausa os cinco DAGs (`docker compose exec airflow-apiserver airflow dags unpause ...`).
- `tunel`: `gcloud compute ssh foota-toota-airflow --tunnel-through-iap -- -N -L 8080:localhost:8080`.
- `senha`: imprime a senha do `admin` de `senhas/senhas.json` local.
- `ligar` / `parar`: `instances start|stop`. `status`: estado da VM e `docker compose ps`.

- [ ] **Step 1:** `bash -n orquestracao/infra.sh orquestracao/vm.sh orquestracao/instalar_docker.sh` → sem saída; `python -m json.tool orquestracao/alerta.json` → ok.
- [ ] **Step 2:** `orquestracao/infra.sh` → termina sem erro; `gcloud projects get-iam-policy pdm-bia-505511 --flatten=bindings[].members --filter=bindings.members~airflow-orquestrador --format='value(bindings.role)'` lista os seis papéis.
- [ ] **Step 3:** `orquestracao/vm.sh criar`, esperar o startup (`gcloud compute ssh ... --tunnel-through-iap -- docker compose version` responde), `orquestracao/vm.sh enviar` → os cinco serviços `healthy`/`running` em `vm.sh status`.
- [ ] **Step 4: Verificar na VM.** Pelo túnel: `coleta_ao_vivo` com 2 execuções verdes seguidas; `saude` verde (com Dataflow drenado, `atraso_predicao` = skipped); `disparar_eventos` com `BSA`, `2026`, rodada do arquivo → Job `succeeded`, eventos em `stream.eventos_brutos` com `mode = replay`.
- [ ] **Step 5: Alerta de ponta a ponta.** `gcloud run jobs execute foota-toota-coletor --args=python,producer.py,replay,--rodadas,99 --region=us-central1 --project=pdm-bia-505511`; disparar o `saude` → `jobs_cloud_run` falha com "execução ... falhou", entrada no log `foota-toota-alertas` e, com `ALERTA_EMAIL`, e-mail em até 5 min.
- [ ] **Step 6:** Pausar os agendamentos antigos, um por vez: `gcloud scheduler jobs pause <nome> --location=us-central1 --project=pdm-bia-505511` para `foota-toota-coletor-5min` e `foota-toota-daily-run`. No cabeçalho de `deploy_coletor.sh`, registrar que o agendamento agora é do Airflow e que `retomar` é o plano B com a VM parada.
- [ ] **Step 7: Commit** `feat(orquestracao): VM do Airflow, service account e alerta por e-mail`

---

### Task 5: Dataflow como Flex Template

**Files:**
- Create: `streaming/Dockerfile.template` — `FROM gcr.io/dataflow-templates-base/python312-template-launcher-base`, `ENV FLEX_TEMPLATE_PYTHON_PY_FILE=/template/pipeline.py`, copia `pipeline.py` e `requirements-pipeline.txt` para `/template/`, `pip install -r`
- Create: `streaming/template_metadata.json` — parâmetros `api_url` e `subscription` (os mesmos nomes de `pipeline.run`)
- Modify: `streaming/dataflow.sh` — subcomando `template`: `gcloud builds submit` da imagem `gcr.io/pdm-bia-505511/foota-toota-partidas-template:latest` e `gcloud dataflow flex-template build gs://foota-toota-505511-stream/dataflow/templates/partidas.json --image=... --sdk-language=PYTHON --metadata-file=streaming/template_metadata.json`

- [ ] **Step 1:** Conferir que `pipeline.run` aceita `--api_url` e `--subscription` como opções do pipeline (o Flex Template passa os parâmetros como `--nome=valor`). Se algum for só `argparse` local sem `known_args`, ajustar e cobrir com um teste em `tests/test_streaming.py`.
- [ ] **Step 2:** `streaming/dataflow.sh template` → `gs://foota-toota-505511-stream/dataflow/templates/partidas.json` existe.
- [ ] **Step 3:** Pela interface do Airflow na VM, `dataflow_liga_desliga` com `ligar` → job `foota-toota-partidas` `Running` em `streaming/dataflow.sh status` e `modelo-api` com `min-instances=1` (`gcloud run services describe modelo-api --region=us-central1 --project=pdm-bia-505511 --format='value(spec.template.metadata.annotations."autoscaling.knative.dev/minScale")'`).
- [ ] **Step 4: Demo de ponta a ponta.** `disparar_eventos` (BSA, 2026, uma rodada do TEST) → em ~2 min, linhas novas em `gold.predicoes` com `mode = 'replay'` e `features_antes_do_jogo = true`; `saude` verde com `atraso_predicao` executado (não skipped).
- [ ] **Step 5:** `dataflow_liga_desliga` com `desligar` → job `Draining`/`Drained` e `minScale` 0.
- [ ] **Step 6: Commit** `feat(streaming): Dataflow como Flex Template, ligado e desligado pelo Airflow`

---

### Task 6: Documentação

**Files:**
- Create: `docs/arquitetura/orquestracao.md` — os cinco DAGs (o que disparam, agenda, o que é falha), como acessar a interface (`vm.sh tunel` + `vm.sh senha`), o roteiro da demo (ligar → disparar → consultar `gold.predicoes` → falha provocada no `saude` → desligar) e custos (VM ligada ~US$ 1,6/dia; `vm.sh parar` fora de uso).
- Modify: `README.md` — o Airflow no diagrama de arquitetura e uma seção curta "Orquestração" apontando para o doc.
- Modify: `docs/arquitetura/contratos.md` — o coletor e o Dataflow agora são acionados pelo Airflow; o Cloud Scheduler ficou como plano B.
- Modify: este plano — marcar os checkboxes feitos.

- [ ] **Step 1:** Escrever os três documentos, sem referência a disciplina ou entrega.
- [ ] **Step 2:** `make lint` → PASS.
- [ ] **Step 3: Commit** `docs: orquestração com Airflow`
