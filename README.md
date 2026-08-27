# Foota Toota

Plataforma de informações para fãs de futebol.

## Smoke tests da API

O projeto possui scripts para testar a autenticação e consultar partidas,
jogadores e clubes na API Big Balls Data.

### Pré-requisitos

- Bash
- Make
- curl
- jq

### Configuração

Crie o arquivo local de variáveis de ambiente a partir do template:

```bash
cp .env.template .env
```

Adicione ao `.env` uma chave gerada no
[painel da Big Balls Data](https://bigballsdata.com/dashboard/keys):

```dotenv
BIGBALLSDATA_API_KEY=sua_chave_aqui
```

O `.env` está ignorado pelo Git. Nunca versione nem compartilhe uma chave real.

### Comandos

Execute os comandos a partir da raiz do projeto:

| Comando | Descrição |
| --- | --- |
| `make test-user` | Consulta o usuário autenticado em `/v1/user/me`. |
| `make test-matches` | Consulta dez partidas de futebol da Premier League. |
| `make test-player` | Pesquisa Kylian Mbappé e exibe o resultado encontrado. |
| `make test-team` | Pesquisa o Real Madrid e exibe o resultado encontrado. |
| `make test-club-matches` | Cruza as partidas do Real Madrid entre EPL, La Liga e Champions. |
| `make test-api` | Executa todos os smoke tests em sequência. |

A consulta de partidas aceita `SPORT`, `LEAGUE` e `LIMIT`. Os valores padrão
são, respectivamente, `football`, `epl` e `10`.

```bash
LEAGUE=laliga LIMIT=5 make test-matches
```

O teste de jogador usa `Kylian Mbappe` por padrão. Use `PLAYER_NAME` para
pesquisar outro jogador, como Vini Jr ou Lamine Yamal:

```bash
PLAYER_NAME="Vinicius" make test-player
PLAYER_NAME="Lamine Yamal" make test-player
```

A API não encontra o termo `Vini Jr`; a busca por `Vinicius` retorna Vinícius
Júnior como primeiro resultado.

O teste de clube percorre a lista paginada de times de futebol, encontra o Real
Madrid e exibe o resultado. Use `TEAM_NAME` para testar o Barcelona:

```bash
TEAM_NAME="Barcelona" make test-team
```

### Partidas de um clube em várias competições

O teste cruzado consulta `/v1/leagues` para validar os códigos das competições,
busca as partidas de cada liga e unifica os resultados encontrados para o
clube:

```bash
make test-club-matches
```

Por padrão, o teste pesquisa o Real Madrid em `epl`, `laliga` e `ucl`. É
possível alterar o clube, as competições e a temporada:

```bash
TEAM_NAME="Barcelona" LEAGUES="laliga ucl" make test-club-matches
TEAM_NAME="Arsenal" LEAGUES="epl ucl" SEASON=2026 make test-club-matches
```

As variáveis aceitas são `TEAM_NAME`, `LEAGUES`, `SEASON`, `SPORT` e `LIMIT`.
Os códigos disponíveis podem ser consultados com
`GET /v1/leagues?sport=football`.

Quando `SEASON` não é informado, a API escolhe a temporada padrão de cada
competição de forma independente. Para comparar as mesmas temporadas entre
ligas, informe `SEASON` explicitamente.

Nos resultados avaliados, `home` e `away` não continham IDs de clube. Por isso,
o cruzamento usa o nome do time de forma provisória; o ideal para código de
produção é relacionar as partidas por um identificador estável fornecido pela
API.

As chamadas de detalhes de jogadores e clubes não fazem parte dos smoke tests,
pois a API ainda não possui cobertura para os casos avaliados e essas respostas
foram lentas. Os resultados observados estão registrados em
[`docs/api-smoke-results.md`](docs/api-smoke-results.md).

Os scripts utilizados pelos comandos estão em [`scripts/smoke`](scripts/smoke).

## Referências para ingestão

O catálogo versionado de códigos de competições está em
[`config/league-codes.json`](config/league-codes.json). O arquivo contém as 57
chaves únicas de futebol presentes na referência do provedor, seus aliases e
observações sobre as diferenças encontradas no endpoint `/v1/leagues`.

Esse catálogo deve ser usado para validar e normalizar o campo `league` durante
a ingestão. O valor enviado à API deve ser a propriedade `key`; aliases podem
ser convertidos para a chave canônica antes de persistir os dados.
