# 🧠 Foota Toota — Guia de Dados para Data Science & Machine Learning
**Destinatário:** André (BIA UFG)  
**Projeto GCP:** `pdm-bia-505511`  
**Dataset Silver:** `pdm-bia-505511.silver`  
**Bucket GCS:** `gs://foota-toota-505511/`

---

## 🎯 1. Estratégia de Prova de Conceito (PoC Isolada)

Para atender à necessidade de **validar o pipeline de ponta a ponta com uma única liga por vez** (sem ruído ou data leakage cross-league), foram criadas **duas tabelas físicas isoladas e tratadas** prontas para modelagem.

Elas já passaram por 23 regras de qualidade (placar não-nulo em jogos encerrados, placar nulo em jogos futuros, chaves primárias únicas e datas normalizadas em UTC).

---

## 📋 2. Tabelas de Partidas para a PoC

### A. Campeonato Brasileiro Série A
- **Tabela**: `pdm-bia-505511.silver.matches_brasileirao`
- **Volume**: **8.888 partidas** (Temporadas 2003 a 2026)
  - **8.785 jogos finalizados** (com histórico de placares para treino e validação).
  - **102 jogos agendados para 2026** (para inferência e predição cega).
- **Esquema Principal**:
  - `match_id` (STRING): Identificador único do confronto.
  - `kickoff_utc` (TIMESTAMP): Data e horário do jogo em UTC.
  - `season` (INT64): Ano da temporada (2003 a 2026).
  - `round` (STRING): Rodada do campeonato (ex: `'1'` a `'38'`).
  - `home_team_id` / `away_team_id` (STRING): IDs padronizados dos clubes.
  - `home_team_name` / `away_team_name` (STRING): Nomes dos clubes mandante e visitante.
  - `score_home` / `score_away` (INT64): Gols marcados por mandante e visitante.
  - `outcome` (STRING): Alvo da classificação (`'home'`, `'draw'`, `'away'`).
  - `status` (STRING): `'finished'` ou `'scheduled'`.

### B. Premier League Inglesa (EPL)
- **Tabela**: `pdm-bia-505511.silver.matches_epl`
- **Volume**: **5.269 partidas** (Temporadas 2014 a 2026)
  - **4.589 jogos finalizados** com placar e estatísticas.
  - **680 jogos agendados/recentes**.
- **Esquema**: Idêntico ao do Brasileirão (permitindo reutilizar 100% do código de engenharia de features entre ligas).

---

## 🏆 3. Camada Gold: Feature Stores Prontas para Treino Imediato

Se você não quiser calcular agregações temporais e janelas móveis manualmente, a **Camada Gold** já entrega datasets 100% vetorizados, auditados contra *data leakage* e com splits temporais prontos:

### A. Feature Store do Brasileirão
- **Tabela**: `pdm-bia-505511.gold.match_features_brasileirao`
- **Volume**: **8.888 partidas**
  - **`TRAIN`**: 8.529 jogos com histórico completo e label
  - **`EVAL`**: 256 jogos
  - **`PREDICT`**: 102 jogos futuros agendados

### B. Feature Store da Premier League (EPL)
- **Tabela**: `pdm-bia-505511.gold.match_features_epl`
- **Volume**: **5.269 partidas**
  - **`TRAIN`**: 3.799 jogos com histórico completo e label
  - **`EVAL`**: 380 jogos (temporada 2024/2025)
  - **`TEST`**: 410 jogos (temporada 2025/2026)
  - **`PREDICT`**: 680 jogos futuros agendados

### Features Pré-computadas disponíveis na Gold:
- **Forma Mandante/Visitante**: `home_avg_points_last_5`, `away_avg_points_last_5`, `diff_avg_points_last_5`
- **Poder Ofensivo/Defensivo**: `home_avg_goals_for_last_5`, `away_avg_goals_for_last_5`, `diff_avg_goals_for_last_5`, `home_avg_goals_against_last_5`, `away_avg_goals_against_last_5`
- **Forma na Temporada**: `home_avg_points_season`, `away_avg_points_season`, `diff_avg_points_season`
- **Fadiga / Descanso**: `home_rest_days`, `away_rest_days` (dias desde a última partida oficial)
- **Confronto Direto (H2H)**: `h2h_avg_points_last_5` (aproveitamento nos últimos 5 embates entre os dois)
- **Rótulo Alvo**: `label_outcome` (`home`, `draw`, `away`)
- **Partição de Modelagem**: `split_set` (`TRAIN`, `EVAL`, `TEST`, `PREDICT`)
- **Auditoria Anti-Leakage**: Arrays `home_history_match_ids` e `away_history_match_ids` comprovando que nenhum jogo futuro entrou nas métricas.

---

## 🔬 4. Dados Complementares para Novas Features & Ratings

Quando você validar a baseline da PoC e quiser incrementar o poder preditivo com novas features, utilize estas tabelas complementares:

### 1. Visão Bilateral para Cálculo de Forma (`silver.team_matches`)
- **Tabela**: `pdm-bia-505511.silver.team_matches` (50.886 linhas — 2 linhas por jogo).
- **Para que serve**: Permite calcular com funções de janela (`OVER (PARTITION BY team_id ORDER BY kickoff_utc ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING)`) o aproveitamento recente do time, média de gols marcados/sofridos nos últimos N jogos, sequências de vitórias e descanso em dias, **sem risco de vazamento temporal**.

### 2. Histórico de Confrontos Diretos (`silver.h2h`)
- **Tabela**: `pdm-bia-505511.silver.h2h` (11.790 registros).
- **Garantia Anti-Leakage**: Auditada pela regra `G2` — contém apenas encontros **estritamente anteriores** à data da partida a ser prevista.

### 3. Cotações e Probabilidades de Mercado (`silver.match_odds`)
- **Tabela**: `pdm-bia-505511.silver.match_odds` (10.433 jogos).
- **Conteúdo**: Odds Bet365 e Pinnacle (`bet365_home_win`, `bet365_draw`, `bet365_away_win`).
- **Uso em ML**:
  - Baseline de benchmark (o modelo de ML bate as probabilidades implícitas das casas?).
  - Target Calibration e cálculo de Valor Esperado (+EV) para apostas de valor.

### 4. Força Econômica do Elenco via Transfermarkt
- **`silver.player_valuations`**: 656.301 avaliações de valor de mercado (€).
- **`silver.transfers`**: 175.165 registros de transferências e compras.
- **Uso em ML**: Agregar o valor de mercado total dos 11 titulares ou do elenco como proxy contínuo da qualidade técnica da equipe.

### 5. Notícias e NLP / Sentimento Pré-Jogo (`silver.news_articles`)
- **Tabela**: `pdm-bia-505511.silver.news_articles` (783 notícias completas).
- **Conteúdo**: Título, texto integral higienizado, portal (*ge*, *BBC Sport*, etc.) e data de publicação.
- **Uso em ML**: Extração de sentimento, identificação de desfalques/lesões ou pressão sobre o técnico via LLM/embeddings antes da partida.

---

## 🐍 4. Como Carregar em Python (Pandas / Scikit-Learn)

### Instalação:
```bash
pip install google-cloud-bigquery pandas db-dtypes scikit-learn
```

### Script de Carregamento e Split Temporal:
```python
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project="pdm-bia-505511")

# Puxar dataset do Brasileirão para a PoC
query = """
    SELECT 
        match_id, kickoff_utc, season, round,
        home_team_id, away_team_id,
        home_team_name, away_team_name,
        score_home, score_away, outcome, status
    FROM `pdm-bia-505511.silver.matches_brasileirao`
    WHERE status = 'finished'
    ORDER BY kickoff_utc ASC
"""

df = client.query(query).to_dataframe()
print(f"Dataset carregado: {df.shape[0]} partidas.")

# Opção 1: Treinar direto a partir da Feature Store Gold (Já vetorizada com todas as features):
query_gold = """
    SELECT 
        diff_avg_points_last_5,
        diff_avg_goals_for_last_5,
        diff_avg_goals_against_last_5,
        diff_avg_points_season,
        home_rest_days,
        away_rest_days,
        h2h_avg_points_last_5,
        split_set,
        label_outcome
    FROM `pdm-bia-505511.gold.match_features_brasileirao`
    WHERE has_full_history = TRUE
"""
df_gold = client.query(query_gold).to_dataframe()

train = df_gold[df_gold["split_set"] == "TRAIN"]
eval_set = df_gold[df_gold["split_set"] == "EVAL"]

features = [
    "diff_avg_points_last_5", "diff_avg_goals_for_last_5",
    "diff_avg_goals_against_last_5", "diff_avg_points_season",
    "home_rest_days", "away_rest_days"
]

X_train, y_train = train[features], train["label_outcome"]
X_eval, y_eval = eval_set[features], eval_set["label_outcome"]
print(f"Treino Gold pronto: {len(X_train)} amostras | Avaliação: {len(X_eval)} amostras")

```

### Exemplo de Query com Engenharia de Forma Recente no SQL:
```sql
SELECT 
    m.match_id,
    m.kickoff_utc,
    m.home_team_name,
    m.away_team_name,
    m.outcome,
    -- Média de pontos nos últimos 5 jogos do mandante em casa
    AVG(tm_home.points) OVER (
        PARTITION BY tm_home.team_id 
        ORDER BY tm_home.kickoff_utc 
        ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
    ) AS home_recent_form,
    -- Média de gols pró nos últimos 5 jogos do visitante
    AVG(tm_away.goals_for) OVER (
        PARTITION BY tm_away.team_id 
        ORDER BY tm_away.kickoff_utc 
        ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
    ) AS away_recent_goals
FROM `pdm-bia-505511.silver.matches_brasileirao` m
JOIN `pdm-bia-505511.silver.team_matches` tm_home 
  ON m.match_id = tm_home.match_id AND tm_home.is_home = TRUE
JOIN `pdm-bia-505511.silver.team_matches` tm_away 
  ON m.match_id = tm_away.match_id AND tm_away.is_home = FALSE
WHERE m.status = 'finished'
ORDER BY m.kickoff_utc DESC;
```
