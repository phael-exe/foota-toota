# 🧠 Foota Toota — Guia de Dados para Data Science & Machine Learning
**Destinatário:** André (BIA UFG)  
**Projeto GCP:** `pdm-bia-505511`  
**Dataset Gold (Feature Stores):** `pdm-bia-505511.gold`  
**Dataset Silver (Dados Conformed):** `pdm-bia-505511.silver`  
**Bucket GCS:** `gs://foota-toota-505511/`

---

## 🎯 1. Estratégia de Prova de Conceito (PoC Isolada)

Para validar o pipeline preditivo de ponta a ponta **sem ruído ou vazamento de dados cross-league**, separamos os dados em duas ligas isoladas:
1. **Campeonato Brasileiro Série A** (`brasileirao_serie_a`)
2. **Premier League Inglesa** (`epl`)

Você tem duas formas de trabalhar:
- **Caminho Expresso (Recomendado)**: Consumir diretamente a **Camada Gold**, onde as features temporais (forma recente, gols, descanso, H2H e splits de treino/teste) já estão **vetorizadas e prontas para treino**.
- **Caminho Customizado**: Consumir a **Camada Silver** para construir suas próprias features, janelas móveis ou modelos não-convencionais (NLP em notícias, ratings ELO customizados, etc.).

---

## 🏆 2. Camada Gold: Feature Stores Prontas para Machine Learning

A camada Gold resolve o problema mais trabalhoso da modelagem de futebol: **engenharia de janelas móveis sem data leakage**. Cada linha representa uma partida, e todas as métricas foram calculadas utilizando **estritamente partidas encerradas anteriores ao kickoff**.

### 📋 Tabelas Gold Dedicadas por Liga

#### A. Feature Store do Brasileirão Série A
- **Tabela BigQuery**: `pdm-bia-505511.gold.match_features_brasileirao`
- **Volume Total**: **8.888 partidas** (Temporadas 2003 a 2026)
  - **`TRAIN`**: **8.529 jogos** (2003 a junho/2024) com histórico completo de 5 jogos e rótulo.
  - **`EVAL`**: **256 jogos** (julho/2024 a maio/2025) para validação fora da amostra de tempo.
  - **`PREDICT`**: **102 jogos agendados para 2026** (para inferência e testes cegos em produção).

#### B. Feature Store da Premier League (EPL)
- **Tabela BigQuery**: `pdm-bia-505511.gold.match_features_epl`
- **Volume Total**: **5.269 partidas** (Temporadas 2014 a 2026)
  - **`TRAIN`**: **3.799 jogos** (2014 a junho/2024).
  - **`EVAL`**: **380 jogos** (temporada 2024/2025 completa).
  - **`TEST`**: **410 jogos** (temporada 2025/2026).
  - **`PREDICT`**: **680 jogos agendados/recentes** para previsão.

---

### 📊 Dicionário de Colunas da Feature Store Gold

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `match_id` | STRING | Identificador único do jogo (ex: `bra_1001` ou `fduk_E0_...`). |
| `league_id` | STRING | Código canônico da liga (`'brasileirao_serie_a'` ou `'epl'`). |
| `kickoff_utc` | TIMESTAMP | Data e horário da partida em UTC. |
| `home_team_id` / `away_team_id` | STRING | IDs normalizados dos clubes mandante e visitante. |
| `home_avg_points_last_5` | FLOAT64 | Média de pontos (0 a 3) do mandante nos últimos 5 jogos da liga. |
| `away_avg_points_last_5` | FLOAT64 | Média de pontos (0 a 3) do visitante nos últimos 5 jogos da liga. |
| `diff_avg_points_last_5` | FLOAT64 | **Diferencial de Forma**: `home_avg_points_last_5 - away_avg_points_last_5`. |
| `home_avg_goals_for_last_5` | FLOAT64 | Média de gols marcados pelo mandante nos últimos 5 jogos. |
| `away_avg_goals_for_last_5` | FLOAT64 | Média de gols marcados pelo visitante nos últimos 5 jogos. |
| `diff_avg_goals_for_last_5` | FLOAT64 | **Diferencial Ofensivo**: `home_goals - away_goals`. |
| `home_avg_goals_against_last_5` | FLOAT64 | Média de gols sofridos pelo mandante nos últimos 5 jogos. |
| `away_avg_goals_against_last_5` | FLOAT64 | Média de gols sofridos pelo visitante nos últimos 5 jogos. |
| `home_avg_points_season` | FLOAT64 | Aproveitamento de pontos acumulado do mandante na temporada atual. |
| `away_avg_points_season` | FLOAT64 | Aproveitamento de pontos acumulado do visitante na temporada atual. |
| `diff_avg_points_season` | FLOAT64 | **Diferencial de Temporada**: `home_season - away_season`. |
| `home_rest_days` | INT64 | Dias de descanso do mandante desde a última partida (limitado a 60). |
| `away_rest_days` | INT64 | Dias de descanso do visitante desde a última partida (limitado a 60). |
| `h2h_avg_points_last_5` | FLOAT64 | Pontos conquistados pelo mandante contra este mesmo adversário nos últimos 5 confrontos diretos. |
| `has_full_history` | BOOL | `TRUE` se ambos os times já possuem histórico de pelo menos 5 jogos anteriores. |
| **`label_outcome`** | STRING | **Target**: `'home'`, `'draw'` ou `'away'` (`NULL` em jogos agendados). |
| **`split_set`** | STRING | **Divisão Temporal**: `'TRAIN'`, `'EVAL'`, `'TEST'` ou `'PREDICT'`. |
| `home_history_match_ids` | ARRAY<STRING> | IDs dos jogos que entraram na média do mandante (Auditoria anti-leakage). |
| `away_history_match_ids` | ARRAY<STRING> | IDs dos jogos que entraram na média do visitante (Auditoria anti-leakage). |

---

## 🛡️ 3. Garantias Anti-Data Leakage (Suíte `sql/05_gold_checks`)

As tabelas Gold foram auditadas por testes determinísticos no BigQuery:
- **Regra G1 (`no_future_history`)**: Nenhuma feature temporal pode conter partidas com kickoff posterior ou igual ao do jogo atual.
- **Regra G2 (`h2h_strictly_earlier`)**: Confrontos diretos históricos são estritamente anteriores.
- **Regra G3 (`no_snapshot_columns`)**: Colunas de classificação geral ou tabelas estáticas não foram misturadas com o fato de partidas.
- **Regra G4 (`label_matches_status`)**: `label_outcome` só existe para jogos `finished`.
- **Regra G5 (`home_share`)**: Proporção histórica validada (46.3% vitórias mandantes, 28.3% visitantes, 25.4% empates).

---

## 🔬 4. Camada Silver: Dados Conformed para Features Customizadas

Se você quiser criar features além das já existentes na Gold, utilize as tabelas da Silver:

| Tabela Silver | Registros | O que contém | Oportunidade de Modelagem |
| :--- | :--- | :--- | :--- |
| `silver.matches_brasileirao` | **8.888** | Partidas limpas do Brasileirão com placares e rodadas. | Modelos de séries temporais ou Poisson de gols. |
| `silver.matches_epl` | **5.269** | Partidas da Premier League com placares e públicos. | Modelos comparativos e cross-league. |
| `silver.team_matches` | **50.886** | Visão bilateral (2 linhas/partida: mandante e visitante). | Janelas móveis customizadas (ex: últimos 3 jogos, apenas jogos em casa). |
| `silver.match_odds` | **10.433** | Cotações pré-jogo (Bet365, Pinnacle). | Benchmark de probabilidades implícitas e cálculo de Valor Esperado (+EV). |
| `silver.player_valuations` | **656.301** | Valor de mercado histórico de atletas em EUR (Transfermarkt). | Proxy da força financeira/qualidade do elenco. |
| `silver.transfers` | **175.165** | Compras/vendas de jogadores e valores pagos. | Taxa de renovação do elenco e investimento recente. |
| `silver.news_articles` | **783** | Notícias esportivas completas (*ge*, *BBC*, *ESPN*). | Features de NLP (análise de sentimento pré-jogo, desfalques, pressão no técnico). |
| `silver.player_gameweeks` | **109.282** | Desempenho semanal no Fantasy Premier League (xG, xA, minutos). | Impacto de ausência de jogadores-chave. |

---

## 🐍 5. Código Pronto em Python (Treino e Predição na Gold)

### Instalação de dependências:
```bash
pip install google-cloud-bigquery pandas scikit-learn db-dtypes
```

### Script de Treino Completo (Baseline para a PoC):
```python
from google.cloud import bigquery
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, accuracy_score, log_loss

# 1. Conexão ao BigQuery
client = bigquery.Client(project="pdm-bia-505511")

# 2. Carregar a Feature Store Gold do Brasileirão
query = """
    SELECT 
        match_id, kickoff_utc, home_team_name, away_team_name,
        -- Features de Forma e Gols
        diff_avg_points_last_5,
        home_avg_points_last_5,
        away_avg_points_last_5,
        diff_avg_goals_for_last_5,
        home_avg_goals_for_last_5,
        away_avg_goals_for_last_5,
        diff_avg_points_season,
        -- Descanso e H2H
        home_rest_days,
        away_rest_days,
        COALESCE(h2h_avg_points_last_5, 1.0) AS h2h_points,
        -- Partição e Rótulo
        split_set,
        label_outcome
    FROM `pdm-bia-505511.gold.match_features_brasileirao`
    WHERE has_full_history = TRUE OR split_set = 'PREDICT'
    ORDER BY kickoff_utc ASC
"""
df = client.query(query).to_dataframe()
print(f"Total de registros carregados: {len(df)}")

# 3. Separar as features preditivas
feature_cols = [
    "diff_avg_points_last_5",
    "home_avg_points_last_5",
    "away_avg_points_last_5",
    "diff_avg_goals_for_last_5",
    "home_avg_goals_for_last_5",
    "away_avg_goals_for_last_5",
    "diff_avg_points_season",
    "home_rest_days",
    "away_rest_days",
    "h2h_points"
]

# 4. Divisão Temporal (Sem risco de data leakage)
train_df = df[df["split_set"] == "TRAIN"]
eval_df  = df[df["split_set"] == "EVAL"]
pred_df  = df[df["split_set"] == "PREDICT"]

X_train, y_train = train_df[feature_cols], train_df["label_outcome"]
X_eval, y_eval   = eval_df[feature_cols], eval_df["label_outcome"]

print(f"Treino: {len(X_train)} amostras | Validação: {len(X_eval)} amostras")

# 5. Treinar Modelo (Gradient Boosting)
model = HistGradientBoostingClassifier(random_state=42, max_iter=100)
model.fit(X_train, y_train)

# 6. Avaliar no conjunto de validação (Fora do tempo)
y_pred = model.predict(X_eval)
y_proba = model.predict_proba(X_eval)

print("\n--- Resultados na Validação (EVAL) ---")
print(f"Acurácia: {accuracy_score(y_eval, y_pred):.2%}")
print(f"Log Loss: {log_loss(y_eval, y_proba):.4f}")
print("\nRelatório de Classificação:")
print(classification_report(y_eval, y_pred))

# 7. Gerar Predições para os Próximos Jogos Agendados (PREDICT)
if len(pred_df) > 0:
    X_future = pred_df[feature_cols]
    pred_probs = model.predict_proba(X_future)
    
    classes = model.classes_ # ['away', 'draw', 'home']
    for cls_idx, cls_name in enumerate(classes):
        pred_df[f"prob_{cls_name}"] = pred_probs[:, cls_idx]
    
    print("\n--- Predições para Próximos Jogos ---")
    print(pred_df[["kickoff_utc", "home_team_name", "away_team_name", "prob_home", "prob_draw", "prob_away"]].head(10))
```
