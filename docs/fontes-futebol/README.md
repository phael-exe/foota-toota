# Catálogo e Pipeline de Fontes de Futebol — Foota Toota

Este diretório documenta as fontes de dados avaliadas e ativas na plataforma **Foota Toota**, consolidando **mais de 1.014.000 registros** ingeridos na camada Bronze no Google Cloud (`pdm-bia-505511`).

---

## 1. Arquivos de Referência do Catálogo

Para evitar redundância de documentação em Markdown, os catálogos estão organizados diretamente em formato tabular estruturado para consulta e importação:

- **[`catalogo.csv`](catalogo.csv)** / **[`catalogo.json`](catalogo.json)**: Mapeamento de 129 fornecedores e produtos avaliados (APIs, portais, feeds, bases abertas, modelos).
- **[`dicionario-normalizado.csv`](dicionario-normalizado.csv)** / **[`dicionario-normalizado.json`](dicionario-normalizado.json)**: Dicionário canônico com 336 campos em 32 entidades.
- **[`dicionario-bigballs-csv.csv`](dicionario-bigballs-csv.csv)**: Mapeamento das colunas locais da Big Balls Data API.
- **[`campos-nativos.csv`](campos-nativos.csv)**: Amostra de campos nativos observados em fornecedores externos.

---

## 2. Bases Integradas e Ativas na Camada Bronze (GCS & BigQuery)

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

---

## 3. Comandos 100% Reproduzíveis

Todos os scripts utilizam o gerenciador de dependências `uv` e credenciais padrão do GCP.

### A. Coleta e Atualização de Notícias com Corpo Completo (Tempo Real)
Coleta notícias esportivas de portais diretos (ge.globo, Gazeta Esportiva, Trivela, Metrópoles, BBC Sport, The Guardian, Sky Sports, AS) e extrai o corpo do texto via HTTP puro:
```bash
uv run python scripts/fetch_news.py
```

### B. Coleta Multi-Liga (Football-Data, Brasileirão Histórico, API)
Baixa dados de 10 ligas europeias (2022–2025) e a série histórica completa do Brasileirão:
```bash
uv run python scripts/fetch_bronze.py
```

### C. Coleta de Transferências, Valorações e Fantasy (Transfermarkt + FPL)
Baixa os snapshots públicos de transferências globais e gameweeks do Fantasy Premier League:
```bash
uv run python scripts/fetch_transfers_and_fantasy.py
```

### D. Execução Serverless no Cloud Run Jobs (Custo Zero / Free Tier)
Disparo manual do job configurado no Google Cloud:
```bash
gcloud run jobs execute foota-toota-news-job --region=us-central1 --project=pdm-bia-505511
```

### E. Leitura Direta dos Dados Públicos em Python / Pandas (Sem Login)
Qualquer pessoa pode carregar os dados diretamente do bucket público:
```python
import pandas as pd

# Exemplo: Brasileirão completo direto do GCS público
url = "https://storage.googleapis.com/foota-toota-505511/bronze/brasileirao_historico/campeonato_brasileiro_full.csv"
df = pd.read_csv(url)
print(df.head())
```

---

## 4. Acesso Público aos Dados

- **Bucket Público:** `gs://foota-toota-505511`
- **Navegador Web:** [https://console.cloud.google.com/storage/browser/foota-toota-505511](https://console.cloud.google.com/storage/browser/foota-toota-505511)
- **Download Direto:** `https://storage.googleapis.com/foota-toota-505511/<caminho_do_arquivo>`
