# Foota Toota

Plataforma de informações para fãs de futebol.

## Smoke tests da API

O projeto possui scripts para testar a autenticação e a consulta de partidas na
API Big Balls Data.

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
| `make test-api` | Executa os dois smoke tests em sequência. |

A consulta de partidas aceita `SPORT`, `LEAGUE` e `LIMIT`. Os valores padrão
são, respectivamente, `football`, `epl` e `10`.

```bash
LEAGUE=laliga LIMIT=5 make test-matches
```

Os scripts utilizados pelos comandos estão em [`scripts/smoke`](scripts/smoke).
