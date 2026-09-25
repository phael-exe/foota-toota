# ⚽ Foota Toota — Catálogo de Dados & Guia de Acesso (Equipe)

Este documento foi preparado para servir de **referência técnica e guia prático** para o início dos trabalhos da equipe (**André**, **Wagner Love** e desenvolvedores/cientistas de dados).

Todos os dados da camada **Silver** já estão limpos, tipados, auditados por 23 regras de qualidade e materializados no **Google BigQuery** (Projeto: `pdm-bia-505511`), além de preservados em arquivos no **Google Cloud Storage** (`gs://foota-toota-505511/`).

---

## 📌 Sumário Executivo

| Recurso | Destino / Identificador | Descrição |
| :--- | :--- | :--- |
| **GCP Project ID** | `pdm-bia-505511` | Projeto unificado na nuvem |
| **Dataset Silver** | `pdm-bia-505511.silver` | 20+ tabelas conformed prontas para consumo analítico e ML |
| **Bucket GCS** | `gs://foota-toota-505511/` | Armazenamento de arquivos brutos (CSVs, Parquet, JSONL) |
| **Região** | `US` | Região multirregional BigQuery/GCS |

---

## 🎯 1. Guia Específico: André (Prova de Conceito / PoC Isolada)

> **Objetivo da PoC**: Validar o pipeline e os modelos preditivos ponta a ponta com escopo estritamente delimitado em **uma única liga por vez**, garantindo zero ruído ou vazamento de outras competições.

Para atender exatamente a esse objetivo, criamos tabelas dedicadas e isoladas no BigQuery:

### 📋 Tabelas Dedicadas para o André

#### 1. Brasileirão Série A (Histórico Completo)
- **Tabela BigQuery**: `pdm-bia-505511.silver.matches_brasileirao`
- **Volume**: **8.888 partidas** (Temporadas 2003 a 2026)
  - 8.785 finalizadas com placar completo.
  - 102 agendadas para 2026.
- **Campos Principais**:
  - `match_id` (STRING): Chave única da partida (ex: `bra_1`, `bra_2`).
  - `kickoff_utc` (TIMESTAMP): Data e hora do jogo em UTC.
  - `home_team_name` / `away_team_name` (STRING): Nomes dos clubes.
  - `score_home` / `score_away` (INT64): Placar final (ex: `2` x `1`).
  - `outcome` (STRING): `'home'`, `'draw'` ou `'away'`.
  - `round` (STRING): Rodada do campeonato (ex: `'1'`, `'38'`).
  - `status` (STRING): `'finished'` ou `'scheduled'`.

#### 2. Premier League Inglesa (EPL)
- **Tabela BigQuery**: `pdm-bia-505511.silver.matches_epl`
- **Volume**: **5.269 partidas** (Temporadas 2014 a 2026)
  - 4.589 finalizadas com placar completo.
  - 680 agendadas/recentes.
- **Campos Principais**:
  - Mesma estrutura canônica da tabela do Brasileirão (`kickoff_utc`, `home_team_name`, `away_team_name`, `score_home`, `score_away`, `outcome`, `linescore_home`, `attendance`).

#### 3. Notícias Esportivas e Sentimento (Texto Integral)
- **Tabela BigQuery**: `pdm-bia-505511.silver.news_articles`
- **Volume**: **783 artigos**
- **Fontes**: *Globo Esporte (ge)*, *BBC Sport*, *Sky Sports*, *ESPN*.
- **Campos Principais**:
  - `article_id` (STRING): Hash único da notícia.
  - `title` (STRING): Título da manchete.
  - `body_text` (STRING): Texto integral higienizado da matéria.
  - `published_at` (TIMESTAMP): Data de publicação UTC.
  - `source` (STRING): Portal de origem.
  - `language` (STRING): `'pt'` ou `'en'`.

---

## 🚀 2. Guia Específico: Wagner Love (Catálogo Completo & Modelagem)

> **Objetivo do Wagner**: Ter a visão 360° de todos os dados disponíveis para construir features avançadas, ratings, classificações, métricas de elenco e modelos preditivos estatísticos/ML.

Além das partidas (PL e Brasileirão) e notícias, você tem acesso imediato aos seguintes dados na camada Silver:

### 📋 Tabelas Adicionais para o Wagner

| Tabela BigQuery | Registros | O que contém | Casos de Uso / Features |
| :--- | :--- | :--- | :--- |
| `pdm-bia-505511.silver.match_stats` | **10.436** | Chutes no gol, chutes totais, faltas cometidas, escanteios e cartões (mandante e visitante). | Expected Goals (xG), pressão ofensiva, agressividade e volume de jogo. |
| `pdm-bia-505511.silver.match_odds` | **10.433** | Cotações pré-jogo de 1X2 (Bet365, Pinnacle, médias e máximas). | Probabilidades implícitas do mercado, benchmark de acurácia dos modelos e identificação de apostas de valor (+EV). |
| `pdm-bia-505511.silver.match_goals` | **12.879** | Registro de cada gol marcado com minutagem, autor e tipo do gol (falta, pênalti, bola rolando). | Padrão de gols no 1º tempo vs 2º tempo, momentum e capacidade de reação. |
| `pdm-bia-505511.silver.standings` | **212** | Posição oficial, jogos disputados, vitórias, empates, derrotas, gols pró/contra e saldo. | Pressão de tabela (zona de rebaixamento, vaga em torneio continental). |
| `pdm-bia-505511.silver.transfers` | **175.165** | Histórico de contratações/vendas, taxas de transferência (€) e clubes envolvidos. | Renovação de elenco, investimento financeiro recente e perda de peças-chave. |
| `pdm-bia-505511.silver.player_valuations` | **656.301** | Valor de mercado de cada atleta (€) atualizado periodicamente pelo Transfermarkt. | Valor de mercado total do elenco (Proxy direto de força relativa do clube). |
| `pdm-bia-505511.silver.match_tactics` | **8.785** | Formações táticas (ex: 4-3-3, 4-2-3-1), técnicos e estádio de cada partida do Brasileirão. | Compatibilidade de esquemas táticos e efeito da troca de comando técnico. |
| `pdm-bia-505511.silver.player_gameweeks` | **109.282** | Métricas semanais por jogador no Fantasy (xG, xA, minutos jogados, clean sheets, ICT). | Forma individual de jogadores e impacto da ausência de atletas em partidas. |
| `pdm-bia-505511.silver.match_weather` | **4.450** | Temperatura (°C), umidade relativa (%) e velocidade do vento no estádio na hora do jogo. | Impacto climático em desempenho atlético e volume de faltas/gols. |

---

## 💻 3. Como Puxar os Dados (Snippets Prontos)

### Opção A: Via Python (Pandas + BigQuery)

Instale as dependências (se necessário):
```bash
pip install google-cloud-bigquery pandas db-dtypes
```

#### Código para carregar os dados diretamente em DataFrames:
```python
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project="pdm-bia-505511")

# 1. Puxar partidas do Brasileirão (para o André)
query_br = """
    SELECT 
        match_id, kickoff_utc, season, round,
        home_team_name, away_team_name,
        score_home, score_away, outcome, status
    FROM `pdm-bia-505511.silver.matches_brasileirao`
    WHERE status = 'finished'
    ORDER BY kickoff_utc DESC
"""
df_brasileirao = client.query(query_br).to_dataframe()
print(f"Brasileirão carregado: {len(df_brasileirao)} partidas.")

# 2. Puxar partidas da Premier League (para o André)
query_epl = """
    SELECT 
        match_id, kickoff_utc, season,
        home_team_name, away_team_name,
        score_home, score_away, outcome, status
    FROM `pdm-bia-505511.silver.matches_epl`
    WHERE status = 'finished'
    ORDER BY kickoff_utc DESC
"""
df_epl = client.query(query_epl).to_dataframe()
print(f"Premier League carregada: {len(df_epl)} partidas.")

# 3. Puxar estatísticas avançadas + odds (para o Wagner Love)
query_stats_odds = """
    SELECT 
        m.match_id, m.league_id, m.kickoff_utc,
        m.home_team_name, m.away_team_name,
        m.score_home, m.score_away, m.outcome,
        s.shots_home, s.shots_away,
        s.shots_on_target_home, s.shots_on_target_away,
        s.corners_home, s.corners_away,
        o.bet365_home_win, o.bet365_draw, o.bet365_away_win
    FROM `pdm-bia-505511.silver.matches` m
    LEFT JOIN `pdm-bia-505511.silver.match_stats` s ON m.match_id = s.match_id
    LEFT JOIN `pdm-bia-505511.silver.match_odds` o ON m.match_id = o.match_id
    WHERE m.status = 'finished'
      AND s.shots_home IS NOT NULL
    ORDER BY m.kickoff_utc DESC
"""
df_analise = client.query(query_stats_odds).to_dataframe()
print(f"Partidas com stats & odds: {len(df_analise)} registros.")
```

---

### Opção B: Via BigQuery Console (Web)

Basta abrir o console do Google Cloud e executar queries padrão:
1. Acesse: https://console.cloud.google.com/bigquery?project=pdm-bia-505511
2. Expanda o projeto `pdm-bia-505511` > dataset `silver`.
3. Você verá todas as tabelas prontas para consulta com interface gráfica.

---

### Opção C: Acesso aos Arquivos Brutos no Google Cloud Storage (Bucket)

Se preferir baixar os arquivos em CSV/Parquet ou sincronizar no seu disco local:

```bash
# Autenticar no gcloud (se ainda não fez)
gcloud auth login
gcloud config set project pdm-bia-505511

# Listar os arquivos disponíveis no bucket
gcloud storage ls gs://foota-toota-505511/
gcloud storage ls gs://foota-toota-505511/bronze/

# Baixar partidas do Brasileirão
gcloud storage cp -r gs://foota-toota-505511/bronze/brasileirao_historico/ ./dados_br/

# Baixar dados da Premier League e ligas europeias (Football-Data UK)
gcloud storage cp -r gs://foota-toota-505511/bronze/football_data_uk/ ./dados_fduk/

# Baixar transferências e valores de mercado do Transfermarkt
gcloud storage cp -r gs://foota-toota-505511/bronze/transfermarkt/ ./dados_transfermarkt/

# Baixar dados de Fantasy Premier League (FPL)
gcloud storage cp -r gs://foota-toota-505511/bronze/fpl_gameweeks/ ./dados_fpl/

# Baixar feeds de notícias brutas (RSS)
gcloud storage cp -r gs://foota-toota-505511/bronze/news_rss/ ./dados_noticias/
```

---

## 🛡️ 4. Garantia de Qualidade dos Dados

Todas as tabelas passaram por **23 verificações automatizadas de integridade**:
- **Consistência de Resultados**: Jogos finalizados sempre têm placares válidos; jogos futuros possuem placares rigorosamente nulos.
- **Prevenção de Vazamento Temporal (Data Leakage)**: Dados de histórico (H2H) contêm apenas partidas estritamente anteriores ao jogo em questão.
- **Odds e Metadados Validados**: Odds sempre superiores a 1.0; valores de transferência e mercado não-negativos; minutos em campo entre 0 e 120.
- **Resolução de Identidade**: Clubes mapeados por IDs canônicos, eliminando divergências de grafia entre provedores.
