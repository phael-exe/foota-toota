# 🧠 Guia Rápido — Data Science & ML (André)

**Projeto GCP:** `pdm-bia-505511`

---

## 🏆 1. Tabelas Gold Prontas (Feature Stores com Labels e Splits)

As tabelas abaixo já possuem **forma recente, saldo de gols, descanso e H2H calculados sem vazamento temporal**:

| Tabela BigQuery | Liga | Registros | Splits Disponíveis |
| :--- | :--- | :--- | :--- |
| `pdm-bia-505511.gold.match_features_brasileirao` | **Brasileirão** | **8.888** | 8.529 `TRAIN` \| 256 `EVAL` \| 102 `PREDICT` |
| `pdm-bia-505511.gold.match_features_epl` | **Premier League** | **5.269** | 3.799 `TRAIN` \| 380 `EVAL` \| 410 `TEST` \| 680 `PREDICT` |

### Colunas Principais:
- **Features**: `diff_avg_points_last_5`, `diff_avg_goals_for_last_5`, `diff_avg_points_season`, `home_rest_days`, `away_rest_days`, `h2h_avg_points_last_5`.
- **Target**: `label_outcome` (`'home'`, `'draw'`, `'away'`).
- **Divisão**: `split_set` (`'TRAIN'`, `'EVAL'`, `'TEST'`, `'PREDICT'`).

---

## 🐍 2. Como Carregar e Treinar (Python / 15 Linhas)

```python
from google.cloud import bigquery

client = bigquery.Client(project="pdm-bia-505511")

# Puxar Feature Store do Brasileirão (ou troque para _epl)
query = """
    SELECT 
        diff_avg_points_last_5, diff_avg_goals_for_last_5,
        home_rest_days, away_rest_days,
        h2h_avg_points_last_5,
        split_set, label_outcome
    FROM `pdm-bia-505511.gold.match_features_brasileirao`
    WHERE has_full_history = TRUE
"""
df = client.query(query).to_dataframe()

# Split temporal sem vazamento
train = df[df["split_set"] == "TRAIN"]
eval_set = df[df["split_set"] == "EVAL"]

X_train, y_train = train.drop(columns=["split_set", "label_outcome"]), train["label_outcome"]
X_eval, y_eval = eval_set.drop(columns=["split_set", "label_outcome"]), eval_set["label_outcome"]
```

---

## 📁 3. Se Precisar dos Dados Brutos (Camada Silver)

Caso prefira criar suas próprias features ou janelas:
- Partidas Brasileirão: `pdm-bia-505511.silver.matches_brasileirao` (8.888 jogos)
- Partidas Premier League: `pdm-bia-505511.silver.matches_epl` (5.269 jogos)
- Odds de Apostas: `pdm-bia-505511.silver.match_odds` (Bet365 / Pinnacle)
- Notícias / NLP: `pdm-bia-505511.silver.news_articles` (783 notícias com texto integral)
