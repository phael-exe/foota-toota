# Foota Toota

Plataforma de informações para fãs de futebol, alimentada pela
[Big Balls Sports Data][api] através do cliente [pitchside][pitchside].

## Requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/) para gerenciar o ambiente
- Uma chave da Big Balls Data, gratuita em [bigballsdata.com][keys]

## Instalação

```bash
make install
cp .env.template .env
```

Adicione a chave ao `.env`:

```dotenv
BIGBALLSDATA_API_KEY=bbs_live_...
```

O `.env` está ignorado pelo Git. Nunca versione uma chave real.

## Configuração

O que não é segredo vive em `config/bigballsdata.toml`, versionado. As chaves
de topo configuram o cliente HTTP; a tabela `[footatoota]` configura a
aplicação.

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

Dois valores merecem explicação. O `read` é de 60 segundos porque endpoints
de detalhe respondem em 15 segundos ou mais, enquanto o `connect` fica em 10
para que um host morto falhe rápido. O cache em disco existe porque o plano
gratuito permite mil requisições por dia, e o TTL por rota faz catálogos
sobreviverem entre execuções. `make clean` esvazia esse cache.

## Uso

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

Os testes não tocam a rede: as respostas HTTP são simuladas com `respx`. Um
teste marcado com `@pytest.mark.live` só roda com `uv run pytest -m live` e
exige uma chave válida.

## Estrutura

```
config/bigballsdata.toml  configuração do cliente e da aplicação
config/league-codes.json  catálogo de competições, para normalizar ligas
src/footatoota/           pacote da aplicação
tests/                    suíte, sem acesso à rede
```

## Licença

MIT. Ver [LICENSE](LICENSE).

[api]: https://bigballsdata.com
[keys]: https://bigballsdata.com/dashboard/keys
[pitchside]: https://pypi.org/project/pitchside/
