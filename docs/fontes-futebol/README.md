# Fontes de dados de futebol — Foota Toota
# Catálogo e Pipeline de Fontes de Futebol — Foota Toota

Pesquisa de **2026-09-14**: **129 fontes, produtos e coleções**, com fichas de acesso, conteúdo, cobertura, limitações e evidência. Futebol brasileiro e internacional; masculino, feminino e categorias de base quando a fonte oferece.
Este diretório documenta as fontes de dados avaliadas e ativas na plataforma **Foota Toota**, consolidando **mais de 1.014.000 registros** ingeridos na camada Bronze no Google Cloud (`pdm-bia-505511`).

## Entregáveis
---

- [Catálogo e dicionário por fonte](catalogo.md): todas as fichas, agrupadas por categoria.
- [Catálogo CSV](catalogo.csv) e [JSON](catalogo.json): filtros, planilha e futura configuração de conectores.
- [Dicionário normalizado](dicionario-normalizado.md): **336 campos em 32 entidades**, com significado, tipo, unidade e granularidade; também em [CSV](dicionario-normalizado.csv) e [JSON](dicionario-normalizado.json).
- [Campos nativos selecionados](campos-nativos.md): **75 campos de sete fontes externas**; [CSV](campos-nativos.csv).
- [Dicionário dos CSVs existentes](dicionario-bigballs-csv.md): **105 colunas dos oito contratos CSV locais**, mais os caminhos JSON usados na silver; [CSV](dicionario-bigballs-csv.csv).
## 1. Arquivos de Referência do Catálogo

## Como ler o resultado
Para evitar redundância de documentação em Markdown, os catálogos estão organizados diretamente em formato tabular estruturado para consulta e importação:

O catálogo é amplo, mas não é um censo de todas as fontes da internet. A contagem inclui produtos comerciais e recortes abertos do mesmo fornecedor, além de candidatos cuja verificação falhou. Não representa 129 APIs operacionais nem 129 origens independentes.
- **[`catalogo.csv`](catalogo.csv)** / **[`catalogo.json`](catalogo.json)**: Mapeamento de 129 fornecedores e produtos avaliados (APIs, portais, feeds, bases abertas, modelos).
- **[`dicionario-normalizado.csv`](dicionario-normalizado.csv)** / **[`dicionario-normalizado.json`](dicionario-normalizado.json)**: Dicionário canônico com 336 campos em 32 entidades.
- **[`dicionario-bigballs-csv.csv`](dicionario-bigballs-csv.csv)**: Mapeamento das colunas locais da Big Balls Data API.
- **[`campos-nativos.csv`](campos-nativos.csv)**: Amostra de campos nativos observados em fornecedores externos.

**“Dicionário” tem três níveis explícitos:** ficha de conteúdo por fonte; nomes nativos quando documentados/observados; modelo comum proposto para cruzar os dados. Schemas completos de todos os fornecedores não são públicos. Campos de interesse não são garantia de entrega por uma API.
---

Pesquisa documental: páginas oficiais, documentação, repositórios dos mantenedores e artigo dos autores. Nenhuma integração autenticada foi executada, nenhuma assinatura foi contratada e nenhuma coleta em massa foi feita. Uma página acessível não comprova latência, cobertura de toda temporada ou autorização para redistribuição. A data acima é a data da consulta; resultados de busca podem refletir indexações anteriores.
## 2. Bases Integradas e Ativas na Camada Bronze (GCS & BigQuery)

| Nível da evidência | Entradas |
|---|---:|
| Documentação pública consultada | 27 |
| Evidência no índice de busca; leitura direta limitada | 5 |
| Página pública consultada; payload não validado | 62 |
| Redirecionamento; oferta atual a confirmar | 1 |
| Repositório consultado | 11 |
| Artigo dos autores consultado | 1 |
| Página acessível com conteúdo parcial | 11 |
| Candidato com validação pendente | 11 |
| Tabela no BigQuery | Fonte | Cobertura | Registros Ingeridos |
|---|---|---|---:|
| `bronze.transfermarkt_player_valuations` | Transfermarkt | Histórico global de valores de mercado | **656.301** |
| `bronze.transfermarkt_transfers` | Transfermarkt | Histórico global de transferências e taxas | **175.165** |
| `bronze.fpl_gameweeks` | Fantasy Premier League | Temporadas 2021 a 2025 com xG, xA, minutos | **109.282** |
| `bronze.transfermarkt_players` | Transfermarkt | Perfis cadastrais de atletas mundiais | **50.149** |
| `bronze.football_data_uk` | Football-Data.co.uk | 10 ligas europeias × 3 temporadas completas com odds | **10.436** |
| `bronze.brasileirao_historico` | Brasileirão Dataset | Todas as edições da Série A de 2003 a 2026 | **8.785** |
| `bronze.football_data_org_matches` | Football-Data.org API | 10 competições Tier One (passadas e futuras até 2027) | **3.134** |
| `bronze.news_rss` | ge.globo, BBC, Guardian, AS, etc. | Notícias esportivas com texto completo do artigo | **903** |
| `bronze.transfermarkt_clubs` | Transfermarkt | Perfis de clubes e federações | **796** |
| `bronze.football_data_org_standings` | Football-Data.org API | Tabelas de classificação oficiais atualizadas | **10** |
| **Total Consolidado** | — | — | **1.014.961** |

## Panorama
---

| Categoria | Fontes/coleções | Exemplos |
|---|---:|---|
| APIs de futebol | 16 | [Big Balls Sports Data](catalogo.md#bigballsdata), [API-Football / API-Sports](catalogo.md#api_football), [Sportmonks Football API](catalogo.md#sportmonks) |
| Dados profissionais | 7 | [Opta / Stats Perform](catalogo.md#opta), [Hudl Statsbomb comercial](catalogo.md#hudl_statsbomb), [Hudl Wyscout comercial](catalogo.md#wyscout) |
| Bases para download | 14 | [StatsBomb Open Data](catalogo.md#statsbomb_open), [Metrica Sports Sample Data](catalogo.md#metrica_open), [SkillCorner Open Data](catalogo.md#skillcorner_open) |
| Portais estatísticos e históricos | 13 | [Transfermarkt](catalogo.md#transfermarkt), [FBref / Stathead](catalogo.md#fbref), [Understat](catalogo.md#understat) |
| Entidades oficiais | 12 | [CBF — competições e documentos](catalogo.md#cbf), [CBF BID](catalogo.md#cbf_bid), [Federação Paulista de Futebol](catalogo.md#fpf_sp) |
| Ligas oficiais | 12 | [Premier League](catalogo.md#premier_league), [English Football League](catalogo.md#efl), [LALIGA](catalogo.md#laliga) |
| Notícias e redações | 21 | [ge](catalogo.md#ge), [UOL Esporte](catalogo.md#uol), [ESPN Brasil](catalogo.md#espn) |
| APIs e descoberta de notícias | 10 | [The Guardian / Open Platform](catalogo.md#guardian), [NewsAPI](catalogo.md#newsapi), [GDELT](catalogo.md#gdelt) |
| Odds e mercados | 7 | [The Odds API](catalogo.md#odds_api), [Betfair Exchange APIs](catalogo.md#betfair), [Pinnacle API](catalogo.md#pinnacle) |
| Ratings e finanças | 6 | [ClubElo](catalogo.md#clubelo), [World Football Elo Ratings](catalogo.md#world_elo), [Euro Club Index](catalogo.md#euroclubindex) |
| Fantasy | 3 | [Fantasy Premier League](catalogo.md#fpl), [Fantasy-Premier-League — vaastav](catalogo.md#fpl_archive), [Cartola](catalogo.md#cartola) |
| Metadados e contexto | 5 | [Wikidata](catalogo.md#wikidata), [Wikimedia Commons](catalogo.md#commons), [OpenStreetMap / Overpass](catalogo.md#osm) |
| Vídeo e transmissão | 3 | [ScoreBat Video API](catalogo.md#scorebat), [YouTube Data API](catalogo.md#youtube), [Live Football On TV](catalogo.md#football_on_tv) |
## 3. Comandos 100% Reproduzíveis

## Fontes que eu priorizaria no projeto
Todos os scripts utilizam o gerenciador de dependências `uv` e credenciais padrão do GCP.

Esta é uma proposta de piloto com base na documentação e no pipeline local, não um ranking obtido por testes comparativos. Como o projeto já tem Big Balls Data e BigQuery, começar validando lacunas concretas evita adicionar fornecedores redundantes.
### A. Coleta e Atualização de Notícias com Corpo Completo (Tempo Real)
Coleta notícias esportivas de portais diretos (ge.globo, Gazeta Esportiva, Trivela, Metrópoles, BBC Sport, The Guardian, Sky Sports, AS) e extrai o corpo do texto via HTTP puro:
```bash
uv run python scripts/fetch_news.py
```

| Necessidade | Primeiro piloto | O que confirmar |
|---|---|---|
| Partidas e estatísticas atuais | Big Balls Data existente + comparação com API-Football ou Sportmonks | Uma liga-temporada completa, campos ausentes, correções e custo por atualização |
| Futebol brasileiro | API Futebol + CBF e federações como referência | Série A/B, estaduais, feminino e base têm coberturas diferentes |
| Histórico para modelos | Football-Data.co.uk, OpenFootball, engsoccerdata, Brasileirão Dataset | Anos efetivos, duplicações, nomes e licenças |
| Eventos, xG e análise tática | StatsBomb Open Data; Wyscout de pesquisa | Recorte temporal, definição das métricas e licença |
| Notícias e descoberta | Guardian Open Platform + GDELT; redações brasileiras nas buscas | Conteúdo autorizado, idioma, janela, origem e deduplicação |
| Transferências | API-Football/Sportmonks; anúncios de clubes; BID para registros brasileiros | Rumor, anúncio, vigência e registro são estados diferentes |
| IDs e estádios | Wikidata + OpenStreetMap | Conciliação de nomes, categorias e localidades |
| Clima | Open-Meteo | Coordenadas, horário de emissão e diferença entre previsão/observação |
| Vídeos | YouTube Data API + ScoreBat | Canal de origem, território e condições de embed |
### B. Coleta Multi-Liga (Football-Data, Brasileirão Histórico, API)
Baixa dados de 10 ligas europeias (2022–2025) e a série histórica completa do Brasileirão:
```bash
uv run python scripts/fetch_bronze.py
```

Referências dos pilotos: [API-Football](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide), [Sportmonks](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures/get-all-fixtures), [BID](https://bid.cbf.com.br/), [StatsBomb Open Data](https://github.com/hudl/open-data), [GDELT DOC](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/).
### C. Coleta de Transferências, Valorações e Fantasy (Transfermarkt + FPL)
Baixa os snapshots públicos de transferências globais e gameweeks do Fantasy Premier League:
```bash
uv run python scripts/fetch_transfers_and_fantasy.py
```

### Mudanças verificadas que alteram a seleção
### D. Execução Serverless no Cloud Run Jobs (Custo Zero / Free Tier)
Disparo manual do job configurado no Google Cloud:
```bash
gcloud run jobs execute foota-toota-news-job --region=us-central1 --project=pdm-bia-505511
```

1. **FBref:** o comunicado de 20/01/2026 informa retirada do fornecedor de dados avançados; não assumir xG detalhado atual. [Sports Reference](https://www.sports-reference.com/blog/category/advanced-stats/).
2. **Pinnacle:** o README oficial informa fechamento do acesso ao público geral em 23/07/2025. [Documentação oficial](https://github.com/pinnacleapi/pinnacleapi-documentation).
3. **Transfermarkt comunitário:** o README informa snapshot até 06/07/2026, sem atualização corrente. É útil para histórico, não para novas transferências em tempo real. [Mantenedor](https://github.com/dcaribou/transfermarkt-datasets).
4. **FotMob:** a própria página proíbe coleta automatizada/sistemática. Integração requer uma via autorizada. [Página oficial](https://www.fotmob.com/).
5. **SoccerNet:** vídeos exigem NDA e a FAQ limita a finalidade a pesquisa. [Download](https://www.soccer-net.org/data) e [FAQ](https://www.soccer-net.org/faq).
### E. Leitura Direta dos Dados Públicos em Python / Pandas (Sem Login)
Qualquer pessoa pode carregar os dados diretamente do bucket público:
```python
import pandas as pd

### Lacunas reais da base atual
# Exemplo: Brasileirão completo direto do GCS público
url = "https://storage.googleapis.com/foota-toota-505511/bronze/brasileirao_historico/campeonato_brasileiro_full.csv"
df = pd.read_csv(url)
print(df.head())
```

A implementação local documenta campos vazios de biografia de jogadores e de contexto de partidas. O SQL de H2H também filtra jogos posteriores à partida consultada. Priorizar uma fonte só por ter o endpoint “players” ou “h2h” não resolve esses problemas; é preciso verificar preenchimento e validade temporal. Ver [dicionário local](dicionario-bigballs-csv.md).
---

O modelo normalizado é uma extensão proposta. Nenhum SQL do pipeline foi alterado. A regra local que deriva temporada por corte em agosto é específica do recorte EPL documentado; numa expansão global, obter a edição da competição explicitamente.
## 4. Acesso Público aos Dados

## Dicionário do próprio catálogo

| Coluna | Significado |
|---|---|
| id | Chave estável desta fonte/produto/coleção. |
| nome / categoria | Nome de consulta e agrupamento principal. |
| acesso | Interface identificada: API, arquivo, site ou contrato. |
| custo | Modalidade geral; não é cotação comercial nem garantia de gratuidade para produção. |
| cobertura | Universo anunciado/observado e ressalvas; não substitui matriz por liga-temporada. |
| entidades | Entidades conceituais a investigar; nomes são chaves do dicionário normalizado. No CSV, separadas por ponto e vírgula. |
| conteudo_interesse | Dados e informações relevantes para o futebol. |
| limitacoes | Lacunas, atualização, mudanças e restrições específicas encontradas. |
| evidencia_url / nivel_evidencia | Referência direta e qualidade da verificação documental. |
| data_consulta | Data da pesquisa; não é a data de atualização dos dados do fornecedor. |
| integracao_testada | False: a pesquisa não fez chamadas autenticadas de integração. |
| schema_nativo_completo | False: nenhuma ficha promete todos os campos de todos os endpoints. |

## Critério para passar do catálogo à ingestão

Para cada piloto, obter um payload permitido e uma liga-temporada conhecida; medir jogos e atletas cobertos, campos ausentes, correções, atraso e volume de chamadas. Guardar o bruto, a versão do schema, a origem e o instante observado. Escolher uma fonte de referência por entidade/campo e manter conflitos rastreáveis.

Frequências de coleta devem ser definidas após esse piloto: live exige política diferente de elencos, notícias, transferências e relatórios anuais. Não foram estimadas latências nem quotas universais a partir de páginas de marketing.

Outras famílias a expandir: sites oficiais de cada clube, federações estaduais/ nacionais ainda não catalogadas, imprensa local e regional, futsal e futebol de areia. Elas são mencionadas como continuidade da busca, sem serem contadas como fontes verificadas.

- **Bucket Público:** `gs://foota-toota-505511`
- **Navegador Web:** [https://console.cloud.google.com/storage/browser/foota-toota-505511](https://console.cloud.google.com/storage/browser/foota-toota-505511)
- **Download Direto:** `https://storage.googleapis.com/foota-toota-505511/<caminho_do_arquivo>`
