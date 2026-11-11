# Pipeline integrado: streaming com inferência, mais ligas e orquestração

Data: 2026-11-11 · Branch: `trabalho-final` · Projeto GCP: `pdm-bia-505511` (único)

## 1. Intenção

Hoje o foota-toota tem a camada batch (bronze → silver → gold no BigQuery), o
streaming (coletor → Pub/Sub → Dataflow → BigQuery) e um modelo servido por
uma API no Cloud Run. Mas essas peças estão soltas em três pontos:

- quem chama a API é uma assinatura push do Pub/Sub, não o pipeline;
- o modelo e a API moram em outro projeto GCP (`pdm-andre-2026`);
- nada orquestra o conjunto: o coletor roda num agendamento solto e o
  Dataflow é ligado e desligado à mão.

O objetivo é fechar o ciclo: **o Dataflow chama a API para cada evento e grava
o evento já com a predição**, tudo num projeto só, operado por um orquestrador
(Airflow). Ao mesmo tempo, ampliamos o domínio para sete competições e
melhoramos o modelo, que hoje bate o baseline por muito pouco (50,1% de
acurácia contra 49,3% do "sempre mandante").

Tudo precisa estar rodando na nuvem e ser demonstrável ao vivo em até 10
minutos, em 2026-12-04. O prazo de entrega do código é 2026-12-02 23:59.

## 2. Objetivos

1. **Streaming com inferência no pipeline.** O Dataflow lê o evento do
   Pub/Sub, faz a requisição HTTP para a API no Cloud Run, anexa a predição
   (classe, probabilidades, versão do modelo) ao evento e grava o evento
   enriquecido no BigQuery. A partir daí ele entra no silver/gold.
2. **Um projeto só.** API, Model Registry, Experiments e tabelas de avaliação
   ficam no `pdm-bia-505511`.
3. **API em módulos.** O `modelo/api.py` (955 linhas) vira um pacote, com
   responsabilidades separadas.
4. **Sete competições.** Brasileirão, Premier League, La Liga, Serie A,
   Bundesliga, Ligue 1 e Champions League, cada uma com o próprio campeão.
5. **Rinha de modelos com a mesma regra de promoção**, aplicada por competição.
6. **Prova de "antes do jogo".** Cada predição mostra quando foi feita e até
   quando vão os dados usados nas features.
7. **Orquestração com Airflow.** O Airflow dispara o coletor, o replay e os
   jobs batch, e checa a saúde dos serviços.
8. **Troca automática da conta de faturamento** quando o crédito de uma conta
   chegar a 90%.

## 3. Não objetivos

- O frontend. O resultado é verificado no BigQuery; o front não muda.
- Um gerador de confrontos fictícios ("Flamengo x Real Madrid"). Fica para
  depois, se sobrar tempo.
- As ligas fora das sete acima (Championship, Eredivisie, Primeira Liga,
  Bélgica, Escócia) continuam no bronze/silver como estão, mas sem modelo.
- Cloud Composer. O custo (US$ 300–400/mês ligado, sem pausa) não cabe nos
  créditos.

## 4. Anti-objetivos (o que seria fracasso mesmo funcionando)

- Uma predição que usa dados de depois do apito inicial: vazamento invalida
  o número de acerto.
- Eventos de replay misturados com eventos ao vivo nas métricas ou no
  `partidas_atual`.
- Promover um modelo sem compará-lo com o campeão, ou escolher hiperparâmetros
  olhando o `TEST`.
- Credencial pessoal (token do e-mail de alguém) dentro de um serviço.
- O projeto parar porque o crédito de uma conta zerou antes da troca.
- A demo depender de haver jogo acontecendo na hora.

## 5. Restrições

- **Projeto:** `pdm-bia-505511`. Todo comando `gcloud`/`bq` leva o projeto
  explícito: o projeto padrão local aponta para outro projeto.
- **Fonte ao vivo:** Football-Data.org, plano grátis, 10 requisições/min. As
  sete competições estão no plano grátis.
- **Créditos:** a conta de faturamento atual mais duas contas de educação
  novas, sem cartão. Uma conta sem crédito é fechada e desliga o projeto.
- **Avaliação do código:** tratamento de erro e eficiência nas requisições do
  pipeline; DAGs e SQL legíveis; README com diagrama de arquitetura.
- **Documentação do repositório:** escrita como projeto, sem referência a
  disciplina ou entrega.

## 6. Estado atual relevante

- `silver.matches` já tem as sete competições, mas com história desigual:
  Brasileirão desde 2003, Premier desde 2014, as outras quatro ligas desde
  2022-23, e a Champions só a temporada atual (144 jogos).
- O modelo e a API cobrem só Brasileirão e Premier (`api.LIGAS`).
- `streaming/pipeline.py` já conhece os ids das sete competições.
- `streaming/producer.py` já tem os modos `live` e `replay`.
- `modelo/treinar.py` já implementa a regra de promoção e grava runs no
  Vertex AI Experiments.

## 7. Decisões

### 7.1 Dados: mais ligas e modelo de dados

- **Times numa tabela única**, independente da liga, com o id do
  Football-Data.org como chave (o mesmo id em todas as competições). O
  `silver.map_team_identity` liga esse id aos ids das outras fontes.
- **Partidas numa tabela única**, com a coluna de competição, particionada
  por data e clusterizada por competição. Não haverá uma tabela por liga. Os
  jogos de um time fora da liga dele (Champions) são linhas dessa mesma
  tabela.
- **História:** aprofundar as quatro ligas que começam em 2022-23 com
  temporadas anteriores do Football-Data.co.uk. Buscar a história da
  Champions (fonte a definir pelo construtor; ver §9).
- **Champions com contexto da liga nacional.** Para cada time da fase de
  liga da Champions, as features incluem a forma recente dele na liga
  nacional.
- **Todas as features são "como estavam antes do jogo".** Cada linha da
  gold de features guarda `features_ate`, o instante do último dado usado,
  sempre menor que o kickoff.
- **Força comparável entre ligas.** Um rating único por time (tipo Elo),
  calculado em ordem cronológica sobre todas as partidas: o rating usado
  numa partida é o de antes dela, nunca um cálculo global que já viu o
  futuro. Os jogos da Champions conectam as ligas
  e calibram o rating entre elas. Isso é a base para a modelagem em grafo
  que o time quer explorar (times como nós, partidas como arestas).

### 7.2 Modelo: um projeto, API em módulos, rinha

- **Re-treinar e registrar no `pdm-bia-505511`**, sem migrar artefatos do
  `pdm-andre-2026`: o modelo vai mudar com as ligas novas de qualquer jeito,
  e o e-mail do Raphael não tem acesso ao projeto antigo.
- **API como pacote** (`modelo/api/`), separando no mínimo: configuração,
  features, registry/carregamento de modelos, predição, avaliação e rotas.
  O contrato HTTP atual (`POST /predict`) se mantém.
- **Regra de promoção** (a mesma de hoje), por competição. Um candidato só
  vira `campeao` daquela competição se, no `TEST` dela, bater:
  1. o "sempre mandante" em acurácia;
  2. as frequências do treino em log loss;
  3. o campeão atual, reavaliado no mesmo `TEST`.

  Empate não promove. Toda tentativa vira um run no Vertex AI Experiments,
  aprovada ou não.
- **Rinha:** o modelo do Raphael, o do André e um eventual modelo global (com
  a competição como coluna) são candidatos iguais. Cada um disputa
  competição por competição.
- **Formato de um candidato:** um estimador scikit-learn serializado em
  `.joblib` mais a lista das features que ele usa, todas presentes na gold
  de features. Um modelo BigQuery ML só entra exportado nesse formato. A
  API e a regra de promoção leem a lista de features de cada versão, em vez
  de um vetor fixo.
- **Competição sem campeão:** o Dataflow grava o evento sem predição, com o
  motivo `sem_campeao`. Nenhum modelo reprovado é servido.
- **Champions:** o `TEST` de uma temporada é pequeno demais para a
  comparação ser estável. O `TEST` da Champions usa várias temporadas, ou
  um corte por data.
- **Resultados expostos por competição**, incluindo as competições em que
  ninguém bate o baseline.

### 7.3 Streaming com inferência

- O Dataflow lê `eventos-dataflow`. Para os eventos de jogo **ainda não
  iniciado**, ele chama `POST /predict` no Cloud Run e anexa a resposta ao
  evento. Os eventos de jogo em andamento ou encerrado seguem sem chamada:
  eles são o resultado real usado na avaliação.
- **Autenticação:** a service account dos workers do Dataflow tem
  `roles/run.invoker` na API e envia um ID token.
- **Robustez:** timeout por requisição, retry com backoff exponencial para
  erros transitórios (5xx, timeout, 429) e nenhum retry para 4xx. O evento
  que esgota as tentativas vai para uma tabela de falhas com o motivo, e
  nunca é descartado em silêncio.
- **Eficiência:** sessão HTTP reaproveitada por worker. As chamadas vão em
  lote quando a API aceitar lote (ver §9).
- **Idempotência:** o `prediction_id` continua determinístico (evento +
  modelo + versão), então um retry não duplica predição na gold.
- **A assinatura push `eventos-api` é removida**, e a API para de publicar
  no tópico `predicoes`. O Dataflow passa a ser o único caminho.
- **Cold start:** a API leva ~24 s para subir do zero. O Airflow sobe
  `min-instances=1` antes da demo e volta para 0 depois.

### 7.4 Prova de "antes do jogo"

Cada predição grava:

| campo | significado |
|---|---|
| `predito_em` | quando a API respondeu |
| `kickoff` | início do jogo |
| `features_ate` | data/hora do último dado usado nas features |
| `modo` | `ao_vivo` ou `replay` |

- **Ao vivo:** a gold expõe `prevista_antes_do_jogo = predito_em < kickoff`.
  O acerto "oficial" para métricas e slides conta só jogos ao vivo previstos
  antes do kickoff.
- **Replay:** a prova é `features_ate < kickoff`. A consulta de demonstração
  mostra as duas colunas lado a lado.
- **O replay da demo usa só rodadas do `TEST`** (ou posteriores ao corte de
  treino) do campeão em produção, para o acerto mostrado não ser dentro da
  amostra. A DAG `disparar_eventos` recusa rodadas que caiam em
  `TRAIN`/`EVAL`.
- **Todo jogo agendado é previsto antes de começar:** o Airflow confere os
  jogos das próximas horas sem predição e republica o evento deles.

### 7.5 Orquestração (Airflow)

- **Airflow numa VM do Compute Engine**, com `docker compose` e
  LocalExecutor. Os DAGs ficam no repositório, em `orquestracao/dags/`.
- **DAGs:**
  - `coleta_ao_vivo`: dispara o coletor (Cloud Run Job) no lugar do
    agendamento atual.
  - `disparar_eventos`: roda o Job de replay com competição e rodada como
    parâmetros. É o "gerador" da demo.
  - `batch_medallion`: atualiza bronze → silver → gold e exporta as tabelas
    públicas.
  - `treino`: roda o `treinar.py` e registra o resultado.
  - `saude`: checa a API (`/health`), os Jobs, o Dataflow e o atraso entre
    evento e predição. Gera um alerta quando algo falha.
  - `dataflow_liga_desliga`: liga o job de streaming antes das janelas de
    jogo ou da demo, e drena depois, para poupar créditos.
  - `prever_pendentes`: garante a predição antes do kickoff (§7.4).
- **Demo:** rodar `disparar_eventos` → mostrar o Dataflow processando →
  rodar a consulta de predição contra o resultado → mostrar o `saude`
  pegando uma falha provocada de propósito.

### 7.6 Troca automática de faturamento

- **Um orçamento em cada conta de faturamento**, com valor igual ao crédito,
  calculado sobre o custo bruto (sem descontar créditos), com limites em
  80% e 90%, publicando no Pub/Sub.
- **Um serviço `troca-faturamento` no Cloud Run**, com service account
  própria. Ele recebe o aviso e:
  - em 80%: registra e avisa;
  - em 90%: liga o projeto na próxima conta da fila
    (`projects.updateBillingInfo`), registra a troca no BigQuery e avisa.
- **A fila das contas** é uma configuração do serviço.
- **Última conta da fila em 90%: desligamento planejado.** O serviço
  drena o Dataflow, volta a API para `min-instances=0`, para a VM do Airflow
  e avisa, em vez de deixar a conta fechar. Para isso a service account tem
  também as permissões de parar esses recursos.
- **Antes de construir:** confirmar que os créditos das contas novas valem
  para qualquer projeto ligado a elas, e não para um projeto específico.
- A DAG `saude` mostra a conta atual e a última troca.
- **Passos manuais**, feitos pelo dono de cada conta de faturamento, uma vez:
  - dar à service account o papel **Usuário da conta de faturamento**;
  - criar os orçamentos, ou dar a quem os cria o papel de gestor de custos
    daquela conta.

## 8. Ordem sugerida

Pelo peso na demonstração e pelas dependências:

1. Modelo e API no `pdm-bia-505511`, já em módulos, com Brasileirão e
   Premier (destrava o resto).
2. Dataflow chamando a API, com tabela de falhas, campos de §7.4 e remoção
   do push.
3. Airflow na VM com `disparar_eventos`, `coleta_ao_vivo` e `saude`.
4. Troca de faturamento (antes da primeira conta chegar a 80%).
5. Mais ligas e história no batch; features da Champions; rating único.
6. Rinha nas sete competições; promover os campeões.
7. DAGs restantes, README com diagrama, slides.

## 9. Deixado para o construtor

- **Fonte da história da Champions.** Verificar quantas temporadas antigas
  o plano grátis do Football-Data.org libera. Se não bastar, escolher outra
  fonte aberta.
- **Endpoint em lote na API**, e o tamanho do lote no Dataflow.
- **Forma de gravar o evento enriquecido:** colunas novas em `stream.partidas`
  ou tabela nova, desde que a gold leia de um lugar só.
- **Canal dos alertas** (e-mail ou outro) e o acesso à interface do Airflow,
  que não pode ficar pública com senha padrão.
- **Tamanho da VM:** um ponto de partida é e2-standard-2.
- **Algoritmo e fórmula do rating único.**
- **Nomes de tabelas e colunas**, seguindo o vocabulário atual (`stream.*`,
  `gold.*`, português).

## 10. Calls feitas por quem escreveu (revisar)

- Re-treinar no `pdm-bia-505511` em vez de copiar artefatos do projeto antigo.
- Uma tabela de partidas única, e não uma por liga.
- O Dataflow só chama a API para jogo ainda não iniciado.
- A API para de publicar em `predicoes`, e o push `eventos-api` sai.
- O acerto "oficial" conta só jogos ao vivo previstos antes do kickoff.
- O `TEST` da Champions com várias temporadas ou por data.
- O Airflow liga/desliga o Dataflow e ajusta o `min-instances` da API.
- Airflow em VM com LocalExecutor.
- Features e rating calculados "como antes do jogo", com `features_ate`.
- Replay da demo restrito a rodadas fora de `TRAIN`/`EVAL`.
- Desligamento planejado quando a última conta chega a 90%.
- Candidato = `.joblib` scikit-learn + lista de features (combinar com o
  André).
- Competição sem campeão fica sem predição (`sem_campeao`).
