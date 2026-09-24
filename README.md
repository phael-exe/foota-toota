# Foota Toota

Plataforma de informações para fãs de futebol, alimentada pela
[Big Balls Sports Data][api] através do cliente [pitchside][pitchside].
Sobre esses dados, um pipeline medalhão em BigQuery (`sql/`) prevê o
resultado das partidas da Premier League com BigQuery ML.

[![CI][ci-badge]][ci]
[![Python][python-badge]][python]
[![License: MIT][license-badge]][license]
[![uv][uv-badge]][uv]
[![Ruff][ruff-badge]][ruff]
[![pre-commit][pre-commit-badge]][pre-commit]

## Catálogo de fontes de futebol

O [levantamento de fontes](docs/fontes-futebol/README.md) reúne 129 fontes,
produtos e coleções para partidas, notícias, jogadores, transferências e
outros dados. Inclui fichas com evidências e limitações, exportações CSV/JSON,
um dicionário normalizado proposto e os campos dos CSVs já usados pelo
projeto. Candidatos pendentes de validação estão identificados.

## Requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/) para gerenciar o ambiente
- Uma chave da Big Balls Data, gratuita em [bigballsdata.com][keys]
- Para o pipeline: o [Google Cloud SDK][gcloud] (`gcloud` e `bq`) autenticado
  em um projeto com BigQuery e Cloud Storage habilitados

## Instalação

```bash
make install
cp .env.template .env
```

Adicione a chave e o projeto ao `.env`:

```dotenv
BIGBALLSDATA_API_KEY=bbs_live_...
GCP_PROJECT_ID=meu-projeto
GCS_BUCKET=meu-bucket
```

No Windows com Git Bash, troque `BQ_BIN=bq` por `BQ_BIN=bq.cmd`. O `.env`
está ignorado pelo Git. Nunca versione uma chave real.

## Configuração

O que não é segredo é versionado em `config/bigballsdata.toml`. As chaves
de topo configuram o cliente HTTP, enquanto a tabela `[footatoota]`
configura a aplicação.

```toml
base_url = "https://api.bigballsdata.com"
max_retries = 3

[timeout]
connect = 10.0
read = 60.0

[cache]
backend = "disk"
max_entries = 512

[footatoota]
log_level = "INFO"
api_log_level = "INFO"
json_logs = false
default_sport = "football"
default_page_size = 200
```

A precedência é: argumento explícito, depois variável de ambiente, depois o
arquivo, depois os padrões. As chaves do cliente aceitam o prefixo
`PITCHSIDE_` e as da aplicação o prefixo `FOOTATOOTA_`.

## Uso

### Pipeline de dados

Os dados foram adquiridos da Big Balls Data com a CLI do cliente
[pitchside][pitchside], disponível no PyPI, uma tabela CSV por endpoint;
`src/` guarda apenas a configuração desse cliente. A partir dos CSVs, três
comandos levam até a previsão da próxima rodada. Tudo roda dentro do
BigQuery; a máquina local só envia arquivos e dispara consultas.

```bash
gcloud auth login
cd sql
./ingest.sh                   # 1. CSVs de data/epl -> gs://GCS_BUCKET
./run.sh [0-9]*               # 2. bronze -> silver -> gold -> modelos (~20 min)
./run.sh model_query.sql      # 3. próximas 10 partidas com previsão
```

1. **Ingestão** (`sql/ingest.sh`). Copia com `gcloud storage cp` os CSVs
   da captura para o bucket, criando o bucket se não existir. A captura de
   08/09/2026 (28 arquivos, 174 MiB) fica em `data/epl`, pasta ignorada
   pelo Git; outra pasta pode ser passada como argumento. O script exige
   os oito arquivos que a bronze lê e sobe os demais como evidência.
2. **Pipeline** (`sql/run.sh`). Executa cada `.sql` na ordem das pastas,
   um statement por arquivo, trocando `PROJECT` e `BUCKET` pelos valores
   do `.env`. Aceita pastas ou arquivos; `./run.sh 04_gold 08_prediction`
   refaz só a gold e a previsão. Uma regra que falha (`ASSERT`) para a
   execução ali. A saída de cada script fica em `sql/out/`.
3. **Consulta ao modelo** (`sql/model_query.sql`). `ML.PREDICT` na árvore
   de decisão e no modelo de gols, com nome dos times.

| Pasta | O que cria |
| --- | --- |
| `00_setup` | Datasets `bronze`, `silver`, `gold`, `quality`; UDF `blank_to_null`. |
| `01_bronze` | Oito tabelas externas sobre o bucket e suas cópias com `batch_id`, `ingested_at` e `source_file`. |
| `02_silver` | Tipos, chaves e deduplicação: `matches`, `teams`, `team_matches`, `h2h`, etc. |
| `03_silver_checks` | Regras S1 a S15 como `ASSERT`; quarentenas em `quality.occurrences`. |
| `04_gold` | `match_features`: 15 atributos por partida, só de jogos anteriores ao kickoff. |
| `05_gold_checks` | Regras G1 a G5, incluindo a prova de zero vazamento temporal. |
| `06_model` | Regressão logística, árvore (`BOOSTED_TREE_CLASSIFIER`) e dois regressores de gols. |
| `07_evaluation` | Métricas no conjunto de teste e comparação entre modelos. |
| `08_prediction` | Previsões para as partidas agendadas. |
| `09_report` | View `quality.report`. |

`./run.sh healthcheck.sql` confere em segundos, sem alterar nada, se o
pipeline está de pé na nuvem. Diagramas de cada camada, o roteiro da
apresentação e o notebook de demonstração estão em `docs/`.

### Cliente da API

```python
from footatoota import AppConfig, configure_logging, create_client

configure_logging(AppConfig())

with create_client() as client:
    table = client.standings.get(league="epl")[0]
    for row in table.top(5):
        print(row.rank, row.team_name, row.league_points)
```

`create_async_client` devolve o equivalente assíncrono. Para inspecionar de
onde veio cada opção antes de conectar, use `load_settings().explain()`.

O comando `footatoota` verifica a configuração e a conexão, imprimindo a
procedência de cada opção, o plano da conta e a saúde do serviço:

```bash
uv run footatoota
```

O `configure_logging` faz os logs do cliente atravessarem o `structlog`,
preservando os campos estruturados da API:

```
[debug] <-- GET /v1/sports 200 in 640ms  elapsed_ms=640 rate_limit=30
        rate_remaining=29 request_id=5d4ea4a5 status=200 cache=hit
```

## Desenvolvimento

| Comando | O que faz |
| --- | --- |
| `make install` | Sincroniza dependências e instala os hooks. |
| `make format` | Aplica `ruff check --fix` e `ruff format`. |
| `make lint` | Verifica lint e formatação. |
| `make typecheck` | Roda o `ty`. |
| `make test` | Roda a suíte, sem os testes marcados `live`. |
| `make test-cov` | Roda a suíte com cobertura. |
| `make check` | Lint, tipos e testes, o mesmo que a CI. |
| `make clean` | Esvazia o cache em disco do cliente. |

As respostas HTTP nos testes são simuladas com `respx`. Um teste marcado
com `@pytest.mark.live` só roda com `uv run pytest -m live` e exige uma
chave válida.

## Licença

MIT. Ver [LICENSE](LICENSE).

[api]: https://bigballsdata.com
[ci]: https://github.com/phael-exe/foota-toota/actions/workflows/ci.yml
[ci-badge]: https://github.com/phael-exe/foota-toota/actions/workflows/ci.yml/badge.svg
[gcloud]: https://cloud.google.com/sdk/docs/install
[keys]: https://bigballsdata.com/dashboard/keys
[license]: LICENSE
[license-badge]: https://img.shields.io/badge/license-MIT-green.svg
[pitchside]: https://pypi.org/project/pitchside/
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-badge]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
[python]: https://www.python.org/downloads/
[python-badge]: https://img.shields.io/badge/python-3.12+-blue.svg
[ruff]: https://github.com/astral-sh/ruff
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[uv]: https://github.com/astral-sh/uv
[uv-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
