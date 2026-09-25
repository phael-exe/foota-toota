# Camada Silver — Foota Toota

A camada **Silver** consolida, limpa, tipa e normaliza os dados brutos da camada Bronze (> 1.014.000 registros), transformando fontes heterogêneas (CSVs, JSON Lines, GZIP) em um **Modelo Canônico Integrado** de futebol no Google BigQuery.

---

## 1. Arquitetura e Entidades da Camada Silver

As transformações estão versionadas e ordenadas em `sql/02_silver/`, gerando tabelas particionadas e clusterizadas para máxima performance analítica:

| Script | Tabela Gerada | Tipo | Fontes de Origem | Conteúdo e Regras de Limpeza |
|---|---|---|---|---|
| `01` | `silver.leagues` / `silver.competitions` | Dimensão | Seed + BBD + Football-Data | 12 competições unificadas (EPL, Brasileirão, La Liga, Serie A, etc.) com códigos ISO-2 e tiers. |
| `02` | `silver.teams` | Dimensão | Transfermarkt + BBD + Ligas | Diretório global de clubes (796 clubes Transfermarkt + BBD + times de todas as ligas). |
| `03` | `silver.players` | Dimensão | Transfermarkt + BBD | 50.149 atletas mundiais com datas de nascimento tipadas, biografia, posições e alturas. |
| `04` | `silver.matches` | Fato Central | Football-Data UK + Brasileirão + FD.org + BBD | Fato unificado de partidas (> 25.000 jogos). Deduplicação por chave canônica, status padronizado (`finished`, `scheduled`), particionado por `DATE(kickoff_utc)`. |
| `05` | `silver.team_matches` | Fato Desdobrado | `silver.matches` | 2 linhas por partida (mandante e visitante), pontuação (3/1/0) e gols para cálculo direto de forma esportiva. |
| `06` | `silver.h2h` | Fato Satélite | `stored_matches_h2h` | Confrontos diretos históricos estritamente anteriores ao kickoff (EPL). |
| `07` | `silver.match_weather` | Fato Satélite | `matches_weather` | Condições climáticas na arena da partida (temperatura, umidade, vento). |
| `08` | `silver.match_goals` | Fato Satélite | `matches_events` | Minutagem e autores de gols por partida. |
| `09` | `silver.position_map` | Mapeamento | BBD | Mapeamento canônico de posições táticas. |
| `10` | `silver.player_match_stats` | Fato Satélite | `stored_matches_stats_players` | Estatísticas individuais por atleta na partida (passes, desarmes, finalizações). |
| `11` | `silver.map_team_identity` | De-Para | Todas as fontes | Resolução de identidade de nomes de clubes entre provedores e grafias. |
| `12` | `silver.match_stats` | Fato Satélite | Football-Data.co.uk | Chutes a gol, faltas, escanteios e cartões amarelos/vermelhos (10 ligas europeias). |
| `13` | `silver.match_odds` | Fato Satélite | Football-Data.co.uk | Odds pré-jogo 1X2 e Over/Under 2.5 gols (Bet365, Pinnacle, médias e máximas). |
| `14` | `silver.match_tactics` | Fato Satélite | Brasileirão Histórico | Formações táticas mandante/visitante, técnicos e arena (2003-2026). |
| `15` | `silver.player_valuations` | Fato Mercado | Transfermarkt | 656k registros históricos de valor de mercado em EUR por atleta ao longo do tempo. |
| `16` | `silver.transfers` | Fato Mercado | Transfermarkt | 175k transferências históricas com clubes de origem/destino e taxas de transferência. |
| `17` | `silver.player_gameweeks` | Fato Performance | Fantasy Premier League | 109k registros de gameweeks com métricas avançadas (xG, xA, minutos, ICT index, pontos). |
| `18` | `silver.news_articles` | Fato Conteúdo | News RSS (ge, BBC, etc.) | 903 notícias esportivas completas, com corpo integral higienizado e timestamps UTC. |
| `19` | `silver.standings` | Fato Classificação| Football-Data.org | Tabelas de classificação oficiais atualizadas das competições ativas. |
| `20` | `report_row_counts` | Relatório | Todas as tabelas Silver | Auditoria instantânea de volumetria de toda a camada. |

---

## 2. Padrões de Higienização e Tipagem

1. **Eliminação de Brancos e Strings Vazias**: Toda coluna de texto passa pela UDF `PROJECT.silver.blank_to_null()`.
2. **Conversões Seguras**: Conversões para `INT64`, `FLOAT64`, `TIMESTAMP` e `DATE` utilizam `SAFE_CAST` e `SAFE.PARSE_TIMESTAMP`.
3. **UTC Universal**: Todas as datas e horas de jogos e publicações são harmonizadas em UTC.
4. **Idempotência**: Todas as tabelas utilizam `CREATE OR REPLACE TABLE`, permitindo reexecuções seguras a qualquer momento.

---

## 3. Governança e Regras de Qualidade (`sql/03_silver_checks/`)

A suíte de qualidade executa 23 testes automatizados após a construção da Silver:

### Regras Bloqueantes (`ASSERT` — interrompem o pipeline se violadas)
- **S1**: Unicidade estrita de `match_id` em `silver.matches`.
- **S2**: Clubes da partida devem ser distintos (`home_team_id != away_team_id`).
- **S3**: Integridade referencial: ambos os clubes de cada partida devem existir em `silver.teams`.
- **S4**: Consistência de placar vs status (`finished` exige placar; `scheduled` exige placar nulo).
- **S5**: Vocabulário de status conhecido (`finished`, `scheduled`, `postponed`, `in_play`, `cancelled`).
- **S6 / S6b**: `league_id` normalizado em caixa baixa e join de competição não-vazio.
- **S8**: Colunas vazias na origem continuam nulas na silver.
- **S10**: Partidas com satélite de clima existem na tabela principal.
- **S12**: Colunas temporais promovidas à Silver são estritamente `TIMESTAMP` ou `DATE`.
- **S13**: Exatamente 2 registros por partida em `silver.team_matches`.
- **S15**: Mapa de posições táticas cobre todas as posições observadas.
- **G2**: Histórico H2H estritamente anterior à partida consultada (sem vazamento temporal).
- **S16**: Odds de aposta em `silver.match_odds` estritamente superiores a 1.0.
- **S17**: Valores de mercado e taxas de transferências não-negativos (`>= 0`).
- **S18**: Notícias com corpo de texto preenchido e publicado válido.
- **S19**: Minutos jogados no FPL dentro dos limites físicos da partida (`0 <= minutes <= 120`).

### Quarentenas e Avisos (`quality.occurrences`)
- **S7**: Registra quarentena se `SAFE_CAST` retornar NULL para um valor bruto não-nulo.
- **S9**: Avisa variações de número de partidas por temporada fechada da Premier League.
- **S14**: Registra quarentena se o JSON de estatísticas do jogador for inválido.

---

## 4. Como Executar

Para rodar a camada Silver e suas validações:

```bash
cd sql
./run.sh 02_silver 03_silver_checks
```

O log completo de cada tabela e asserção é salvo em `sql/out/`.
