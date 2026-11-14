# Orquestração

O Airflow aciona as peças que já existem: os Cloud Run Jobs (coletor, replay,
notícias e a atualização do batch), o job de streaming no Dataflow e a escala da
API do modelo. Ele não
processa dados. O trabalho fica nos serviços, e o Airflow decide quando cada um
roda e confere se deu certo.

## Onde roda

- **Airflow 3.3.2** com LocalExecutor e Postgres, em `docker compose`
  (`orquestracao/docker-compose.yaml`), numa VM `e2-standard-2` (`foota-toota-airflow`,
  `us-central1-a`).
- A VM roda com a service account `airflow-orquestrador`, que tem só os papéis que os DAGs usam
  (`orquestracao/infra.sh`). Nenhuma credencial pessoal fica na VM: as tasks pegam o token pelo
  metadata server.
- A interface escuta só em `127.0.0.1:8080` na VM. O acesso é por túnel SSH via IAP, com o
  usuário `admin` e uma senha aleatória gerada na própria VM.
- Os DAGs ficam em `orquestracao/dags/`. As regras de decisão (validar o replay, julgar a saúde)
  ficam em `orquestracao/dags/foota/`, em Python puro e testadas sem Airflow
  (`tests/test_orquestracao.py`).

## DAGs

| DAG | Quando | O que faz | O que é falha |
| --- | --- | --- | --- |
| `coleta_ao_vivo` | a cada 5 min | Executa o Job `foota-toota-coletor` em modo `live` para Brasileirão e Premier League | Execução do Job com erro. Não há nova tentativa: a próxima execução, 5 min depois, faz esse papel |
| `coleta_noticias` | 06:00 UTC | Executa o Job `foota-toota-news-job` (notícias para o bronze) | Execução do Job com erro, depois de 1 nova tentativa |
| `batch_diario` | 09:00 UTC | Executa o Job `foota-toota-batch`, que atualiza o batch e reexporta o bucket público. Depois espera a plataforma carregar a versão nova e avisa o time por e-mail | Job com erro (sem nova tentativa: a coleta gasta a cota do Football-Data.org), manifesto na mesma versão depois do job, ou a plataforma sem a versão nova em 60 min |
| `disparar_eventos` | manual | Gera os eventos da demo: executa o coletor em modo `replay` com competição, temporada, rodadas e intervalo como parâmetros | Temporada dentro de TRAIN/EVAL do modelo, rodadas malformadas ou rodada sem partidas no bronze |
| `saude` | a cada 15 min | Confere a API (`/health`), as execuções dos Jobs, o job do Dataflow e o atraso entre evento e predição | Qualquer uma das checagens abaixo |
| `dataflow_liga_desliga` | manual | `ligar`: sobe o streaming pelo Flex Template e deixa a API com 1 instância quente. `desligar`: drena o job e volta a API para 0 | Erro ao lançar, drenar ou mudar a escala |

### `disparar_eventos` só aceita dados fora da amostra

O treino separa TRAIN, EVAL e TEST por temporada (`gold.match_training_*`). Antes de executar o
Job, o DAG lê a primeira temporada de TEST da competição e recusa qualquer temporada anterior a
ela. Assim o acerto mostrado no replay nunca vem de partidas que o modelo viu no treino.

### Checagens do `saude`

| Task | Checa | Falha quando |
| --- | --- | --- |
| `api_modelo` | `GET /health` da API privada, com ID token, timeout de 60 s (cobre o cold start) | Status diferente de 200 ou nenhuma liga carregada. Liga sem campeão não é falha: é um estado previsto |
| `jobs_cloud_run` | Execuções recentes do coletor e das notícias | Alguma execução falhou nos últimos 30 min, mesmo que outra tenha passado depois |
| `dataflow` | O job mais recente do streaming | O job falhou nos últimos 30 min. Drenado ou cancelado não é falha: é o estado normal fora das janelas de jogo |
| `atraso_predicao` | Com o job rodando, eventos de jogo agendado ainda sem saída do Dataflow ([consulta](../../orquestracao/dags/foota/sql/eventos_sem_predicao.sql)) | Algum evento espera há mais de 10 min. Com o job desligado, a task é pulada: os eventos esperam na assinatura de propósito |
| `exportacao_publica` | O `exported_at` do `_manifest.json` público | O bucket que a plataforma lê está há mais de 36 h sem exportação |

### `batch_diario`: do batch à tela da plataforma

A plataforma (Smart Soccer Hub) lê o bucket público por HTTPS. A cada 30 min, a próxima
requisição relê o `_manifest.json`, e se a `version` mudou ela troca os dados sem deploy. O
manifesto é o último arquivo que a exportação grava, então a troca só acontece com todos os
arquivos no lugar. A plataforma carrega 12 arquivos (`TABELAS_PLATAFORMA` em
`orquestracao/dags/foota/config.py`), e um arquivo que falte derruba a carga inteira.

| Task | O que faz |
| --- | --- |
| `versao_anterior` | Lê a versão publicada antes de rodar |
| `atualizar` | Executa o Job `foota-toota-batch` ([`scripts/atualizar_partidas.sh`](../../scripts/atualizar_partidas.sh)). Ele começa prevendo de novo os jogos dos próximos 7 dias com a gold da véspera (`scripts/repredizer.py`, em `stream.predicoes_lote`). Depois faz a coleta do Football-Data.org e do Football-Data.co.uk (com as odds dos próximos jogos), leva as notícias do bucket para o bronze, reconstrói silver e gold com as checagens e exporta. Uma checagem que falha para o job antes da exportação, e a plataforma continua com a versão anterior |
| `versao_nova` | Confere que o manifesto mudou de versão |
| `plataforma_carregou` | Sensor: a cada 2 min, pergunta a versão a `GET /api/futebol/versao` da plataforma, até ela ser a nova. A própria consulta é a requisição que faz a plataforma reler o manifesto |
| `avisar_time` | Grava no log `foota-toota-avisos` o que mudou (linhas por tabela que a plataforma lê), e a política "foota-toota: dados atualizados" manda o e-mail para `AVISO_EMAILS` |

As predições vão para a plataforma por `gold.predicoes_publicas`, com uma por jogo e no
`match_id` da silver. O stream prevê com o id do Football-Data.org, mas a silver pode guardar o
jogo encerrado com o id de outra fonte. A view acha o jogo de novo por (liga, temporada,
mandante, visitante).

## Alertas e avisos

Toda task que falha grava uma entrada `ERROR` no log `foota-toota-alertas` do Cloud Logging, com
o DAG, a task e a mensagem. Uma política do Cloud Monitoring baseada nesse log manda e-mail para
`ALERTA_EMAIL`, no máximo um a cada 5 minutos. Sem `ALERTA_EMAIL` no `.env`, as falhas continuam
no log e na interface do Airflow.

```bash
gcloud logging read 'logName="projects/pdm-bia-505511/logs/foota-toota-alertas"' \
    --project=pdm-bia-505511 --limit=5 --format='value(timestamp,jsonPayload.mensagem)'
```

O aviso de dados novos vai para outra lista. O `batch_diario` grava uma entrada `NOTICE` no log
`foota-toota-avisos`, e a política "foota-toota: dados atualizados" manda o e-mail para os
endereços de `AVISO_EMAILS`, separados por vírgula (sem eles, para o `ALERTA_EMAIL`). O e-mail
diz a versão, a data da exportação e quantas linhas cada tabela da plataforma ganhou.

## Operação

| Tarefa | Comando |
| --- | --- |
| Service account, firewall, alerta e aviso (uma vez, ou para conferir) | `orquestracao/infra.sh` |
| Publicar o Job `foota-toota-batch` e o agendamento de reserva | `batch/deploy_job.sh` |
| Atualizar o batch e a plataforma agora, fora do horário | `batch/deploy_job.sh rodar`, ou disparar o `batch_diario` |
| Criar a VM (uma vez) | `orquestracao/vm.sh criar` |
| Publicar os DAGs e subir o Airflow | `orquestracao/vm.sh enviar` |
| Abrir a interface em `localhost:8080` | `orquestracao/vm.sh tunel` |
| Senha do `admin` | `orquestracao/vm.sh senha` |
| Ligar ou parar a VM | `orquestracao/vm.sh ligar` / `parar` |
| Publicar o Flex Template do Dataflow (precisa de Docker local) | `streaming/dataflow.sh template` |
| Testar se os DAGs carregam | `orquestracao/testar_dags.sh` |
| Rodar o Airflow na máquina local, com o ADC | `orquestracao/gerar_segredos.sh $(id -u)` e depois `docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d` em `orquestracao/` |

Com o Airflow no ar, os agendamentos antigos do Cloud Scheduler (`foota-toota-coletor-5min`,
`foota-toota-daily-run` e `foota-toota-batch-diario`) ficam pausados. Se a VM estiver parada,
eles são o plano B: `streaming/deploy_coletor.sh retomar` e `batch/deploy_job.sh retomar`. O plano
B do batch atualiza a plataforma, mas sem a conferência e sem o aviso.

## Roteiro de demonstração

1. `dataflow_liga_desliga` com `ligar`: o job sobe em ~2 min e a API fica quente.
2. `disparar_eventos` com uma rodada de TEST (por exemplo `BSA`, `2026`, `30`): o log da task
   mostra cada evento publicado.
3. No BigQuery, as predições chegam em `gold.predicoes` em 1 a 2 min. Depois que o replay publica
   os resultados, `gold.predicoes_avaliadas` mostra os acertos.
4. Para provocar uma falha, execute o coletor com uma rodada que não existe
   (`gcloud run jobs execute foota-toota-coletor --args=python,producer.py,replay,--rodadas,99 ...`)
   e dispare o `saude`: `jobs_cloud_run` falha com o nome da execução, e o alerta chega.
5. `dataflow_liga_desliga` com `desligar`.

## Custos

- A VM custa ~US$ 1,6 por dia ligada (e2-standard-2). Com `vm.sh parar` o custo cai para o disco.
- O Dataflow cobra por hora enquanto roda: fica desligado fora das janelas de jogo e da demo.
- A API com `min-instances=1` cobra a instância parada. O `desligar` volta para 0.
