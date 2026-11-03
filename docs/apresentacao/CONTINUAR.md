# Prompt de continuação: slides do Trabalho 2 (PDM)

Cole o texto abaixo no agente que vai continuar. Ele precisa de acesso ao
navegador logado na conta Google que vê os projetos do GCP
(`pdm-bia-505511` e `pdm-andre-2026`) e de poder editar o Google Slides.

---

Você vai terminar a apresentação do **Trabalho 2: Ingestão em Tempo Real e
Deploy de Modelo**, da disciplina Processamento de Dados Massivos 2026/2 (BIA),
INF/UFG. Grupo: Raphael, André e Wagner. **Prazo: quarta, 4/11/2026, 23:59**,
entregue na Turing:
<https://turing.inf.ufg.br/mod/assign/view.php?id=76305&action=view>.

## O que já está pronto

- **Código unificado na `main`** de <https://github.com/phael-exe/foota-toota>:
  batch (Trabalho 1), streaming (`streaming/`, `sql/10_stream/`) e modelo
  (`modelo/`). A CI da `main` está verde e os 106 testes passam.
- **Deck no Google Slides**, na pasta do Drive "PDM · Trabalho 2 · Foota Toota",
  com 16 slides de texto, diagrama e tabelas. Cada print que falta é uma
  caixa tracejada cinza. O nome da forma é `PRINT: <id>`, e o texto da caixa
  diz o projeto e traz o link "abrir no console" com a URL exata. As caixas
  verdes (`PRINT_REPO: <arquivo>`) são prints que já existem no repositório.
- **Fonte do deck:** `docs/apresentacao/gerar_slides.py`, que gera o `.pptx`.
  Prints locais em `docs/apresentacao/prints/`.
- **API em produção:** <https://modelo-api-3gvoh2dyuq-uc.a.run.app>
  (`/health`, `/predict`, `/docs`).

## O que falta fazer

1. **Ler o enunciado na Turing**, pelo link acima, e conferir se os slides
   cobrem cada item pedido. Se faltar algum item, crie um slide no mesmo
   estilo. A apresentação tem no máximo 10 minutos.
2. **Tirar os prints do console do GCP**, em tela cheia e com o projeto
   certo selecionado no topo. Em cada caixa `PRINT: <id>`, insira a imagem
   na mesma posição e tamanho e apague a caixa.

   | id | Projeto | O que mostrar |
   | --- | --- | --- |
   | `coletor-execucoes` | pdm-bia-505511 | Cloud Run › Jobs › `foota-toota-coletor`, aba de execuções (várias, a cada 5 min) |
   | `scheduler` | pdm-bia-505511 | Cloud Scheduler › `foota-toota-coletor-5min` (frequência `*/5`, última execução ok) |
   | `pubsub-topicos` | pdm-bia-505511 | Pub/Sub › Tópicos: `eventos`, `predicoes`, `predicoes-dlq` |
   | `pubsub-assinaturas` | pdm-bia-505511 | Pub/Sub › Assinaturas: `eventos-bigquery`, `eventos-dataflow`, `eventos-api`, `predicoes-bigquery` (coluna de tipo de entrega visível) |
   | `dataflow-grafo` | pdm-bia-505511 | Dataflow › Jobs › `foota-toota-partidas`, o grafo do job **rodando** |
   | `bq-stream-detalhes` | pdm-bia-505511 | BigQuery › `stream.partidas` › Detalhes (particionado por dia, clusterizado por `league_id, match_id`) |
   | `bq-stream-preview` | pdm-bia-505511 | BigQuery › `stream.partidas_rejeitadas` › Visualização (colunas `reason` e `payload`) |
   | `bq-unificadas` | pdm-bia-505511 | Resultado de `SELECT origem, mode, COUNT(*) FROM gold.partidas_unificadas GROUP BY 1, 2` |
   | `gcs-publico` | pdm-bia-505511 | Cloud Storage › bucket `foota-toota-505511`, pastas `silver/` e `gold/` |
   | `vertex-experiments` | pdm-andre-2026 | Vertex AI › Experiments › `foota-toota-resultado`, runs aprovados e reprovados |
   | `vertex-registry` | pdm-andre-2026 | Vertex AI › Model Registry: `boosted_tree_brasileirao` e `boosted_tree_epl` |
   | `vertex-versoes` | pdm-andre-2026 | Model Registry › `boosted_tree_brasileirao`: versões e o alias `campeao` |
   | `cloudrun-api` | pdm-andre-2026 | Cloud Run › `modelo-api` › Métricas |
   | `cloudrun-logs` | pdm-andre-2026 | Cloud Run › `modelo-api` › Registros, com linhas `fdorg_… -> home (boosted_tree_brasileirao v1)` |
   | `bq-predicoes-vs-real` | pdm-andre-2026 | Resultado de `SELECT * FROM modelo.predicoes_vs_real WHERE mode = 'replay' ORDER BY kickoff_utc` |
   | `bq-acerto-por-versao` | pdm-andre-2026 | Resultado de `SELECT * FROM modelo.acerto_por_versao` |

   Para o Dataflow, os logs e o `predicoes_vs_real` terem o que mostrar,
   rode antes, na raiz do repositório e com o `.env` preenchido:

   ```bash
   streaming/dataflow.sh iniciar
   uv run python streaming/producer.py replay --rodadas 30 --intervalo 1
   ```

   Quando terminar os prints, desligue o Dataflow, que cobra por hora:

   ```bash
   streaming/dataflow.sh parar
   ```

3. **Trocar as caixas verdes `PRINT_REPO: <arquivo>`** pela imagem de
   `https://raw.githubusercontent.com/phael-exe/foota-toota/main/docs/apresentacao/prints/<arquivo>`.
4. **Conferir** se os links de "Código:" e as caixas do diagrama do slide 3
   abrem o arquivo certo no GitHub, e se nenhum texto vazou da caixa.
5. **Exportar em PDF** (Arquivo › Fazer download › PDF) e salvar na mesma
   pasta do Drive, com o nome `Foota-Toota-Trabalho-2.pdf`. Se tiver acesso
   ao repositório, salve também em `docs/apresentacao/` e abra um PR para a
   `main`.
6. **Confirmar com o Raphael** os nomes completos do grupo na capa (hoje só
   aparecem os primeiros nomes) antes da entrega.

Não versione nenhuma chave nem o `.env`. Se algum recurso do GCP não existir
ou estiver vazio, não invente o print: avise o Raphael do que faltou.
