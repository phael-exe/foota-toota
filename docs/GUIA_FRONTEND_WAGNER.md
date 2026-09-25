# 🎨 Foota Toota — Guia de Dados para Front-End & Plataforma
**Destinatário:** Wagner Love  
**Objetivo:** Consumo e exibição visual de dados nas telas, dashboards e componentes da plataforma Foota Toota  
**Projeto GCP:** `pdm-bia-505511`  
**Dataset Silver:** `pdm-bia-505511.silver`  
**Bucket de Arquivos:** `gs://foota-toota-505511/`

---

## 📱 1. Mapeamento: Telas da Plataforma vs Tabelas Silver

A tabela abaixo conecta cada componente visual do Front-end à tabela correspondente na camada Silver:

| Tela / Componente na UI | Tabela no BigQuery | Registros | O que exibir na tela |
| :--- | :--- | :--- | :--- |
| **Calendário & Listagem de Jogos** | `silver.matches` (ou `matches_brasileirao` / `matches_epl`) | **25.443** | Cards com data/hora, escudo/nome dos clubes, placar e rodada. Suporta filtro por campeonato. |
| **Classificação (Tabela de Liga)** | `silver.standings` | **212** | Tabela com posição, clube, pontos (PTS), jogos (J), vitórias (V), empates (E), derrotas (D) e saldo (SG). |
| **Estatísticas do Jogo (Match Center)** | `silver.match_stats` | **10.436** | Barras comparativas de posse de bola, chutes no gol, escanteios, faltas e cartões. |
| **Linha do Tempo de Gols** | `silver.match_goals` | **12.879** | Timeline do jogo: aos quantos minutos saiu o gol, quem marcou e o tipo de gol (pênalti, falta). |
| **Cards de Odds & Apostas** | `silver.match_odds` | **10.433** | Cotações pré-jogo (Bet365 / Pinnacle) para mandante, empate e visitante. |
| **Esquema Tático & Treinadores** | `silver.match_tactics` | **8.785** | Formações táticas no gramado (4-3-3, 4-2-3-1), técnicos dos times e nome do estádio. |
| **Widget de Clima na Arena** | `silver.match_weather` | **4.450** | Temperatura em °C, umidade do ar e vento no estádio no momento da partida. |
| **Feed de Notícias Esportivas** | `silver.news_articles` | **783** | Cards de notícias com título, data relativa (ex: "há 2 horas"), veículo (*ge*, *BBC*) e texto integral. |
| **Mercado de Transferências** | `silver.transfers` | **175.165** | Feed de contratações recentes, valores de compra/venda em € e clubes de origem/destino. |
| **Ranking de Atletas Mais Valiosos** | `silver.player_valuations` | **656.301** | Gráficos de valor de mercado dos jogadores ao longo do tempo. |

---

## 🛠️ 2. Exemplos de Queries Prontas para Endpoints de API / Backend

Se estiver consumindo os dados via Node.js, Python (FastAPI/Flask) ou Next.js API Routes:

### 1. Listagem de Jogos por Rodada ou Recentes (Home / Calendário)
```sql
SELECT 
    match_id,
    league_id,
    season,
    round,
    kickoff_utc,
    home_team_name,
    away_team_name,
    score_home,
    score_away,
    status, -- 'finished' ou 'scheduled'
    outcome -- 'home', 'draw', 'away'
FROM `pdm-bia-505511.silver.matches`
WHERE league_id = @league_id -- ex: 'brasileirao_serie_a' ou 'epl'
ORDER BY kickoff_utc DESC
LIMIT 20 OFFSET @offset;
```

### 2. Tela de Detalhes da Partida (Match Center Completo)
Para montar a página completa de um jogo específico pelo seu `match_id`:
```sql
SELECT 
    m.match_id, m.kickoff_utc, m.status,
    m.home_team_name, m.away_team_name,
    m.score_home, m.score_away,
    -- Estatísticas da Partida
    s.shots_home, s.shots_away,
    s.shots_on_target_home, s.shots_on_target_away,
    s.corners_home, s.corners_away,
    s.fouls_home, s.fouls_away,
    s.yellow_cards_home, s.yellow_cards_away,
    s.red_cards_home, s.red_cards_away,
    -- Odds de Apostas
    o.bet365_home_win, o.bet365_draw, o.bet365_away_win,
    -- Clima na arena
    w.temperature_c, w.humidity_pct, w.wind_speed_kmh
FROM `pdm-bia-505511.silver.matches` m
LEFT JOIN `pdm-bia-505511.silver.match_stats` s ON m.match_id = s.match_id
LEFT JOIN `pdm-bia-505511.silver.match_odds` o ON m.match_id = o.match_id
LEFT JOIN `pdm-bia-505511.silver.match_weather` w ON m.match_id = w.match_id
WHERE m.match_id = @selected_match_id;
```

### 3. Gols da Partida (Linha do Tempo)
```sql
SELECT 
    minute,
    player_name,
    team_name,
    event_type -- ex: 'goal', 'penalty', 'own_goal'
FROM `pdm-bia-505511.silver.match_goals`
WHERE match_id = @selected_match_id
ORDER BY minute ASC;
```

### 4. Tabela de Classificação
```sql
SELECT 
    rank,
    team_name,
    played_games,
    won,
    draw,
    lost,
    points,
    goals_for,
    goals_against,
    goal_difference
FROM `pdm-bia-505511.silver.standings`
WHERE competition_code = @comp_code -- ex: 'BSA' (Brasileirão) ou 'PL' (Premier League)
ORDER BY rank ASC;
```

### 5. Feed de Notícias
```sql
SELECT 
    article_id,
    title,
    published_at,
    source,
    url,
    body_text
FROM `pdm-bia-505511.silver.news_articles`
WHERE language = 'pt' -- ou 'en'
ORDER BY published_at DESC
LIMIT 10;
```

---

## 💡 3. Dicas de Formatação e UX para o Front-End

1. **Fusos Horários**: Todas as datas no banco (`kickoff_utc`, `published_at`) estão em **UTC**. No front-end (React/Vue/Flutter), converta para o horário do usuário:
   ```javascript
   const dataFormatada = new Intl.DateTimeFormat('pt-BR', {
       dateStyle: 'short',
       timeStyle: 'short',
       timeZone: 'America/Sao_Paulo'
   }).format(new Date(kickoff_utc));
   ```

2. **Status Amigáveis**:
   - `status = 'finished'`: Exibir badge verde **"Encerrado"** com o placar final.
   - `status = 'scheduled'`: Exibir badge azul **"Agendado"** com o horário do jogo (placar fica oculto ou com um traço `- x -`).
   - `status = 'postponed'`: Exibir badge amarela **"Adiado"**.

3. **Valores Monetários de Transferências e Elenco**:
   - Os valores de `transfer_fee_eur` e `market_value_eur` estão em Euros (€).
   - Formate na UI como abreviações limpas (ex: `€ 15.000.000` $\rightarrow$ `€ 15M`).

4. **Identificadores das Ligas no Dropdown de Seleção**:
   - `'brasileirao_serie_a'`: Brasileirão Betano
   - `'epl'`: Premier League
   - `'la_liga'`: La Liga
   - `'serie_a'`: Serie A Italiana
   - `'bundesliga'`: Bundesliga
   - `'champions_league'`: Champions League
