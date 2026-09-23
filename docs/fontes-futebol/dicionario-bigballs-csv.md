# Campos dos CSVs Big Balls Data já declarados no projeto

**8 tabelas; 105 colunas no total, contando campos repetidos entre tabelas.**

Inventário completo das colunas externas declaradas em `sql/01_bronze`, lidas localmente. Isto descreve o contrato de CSV do projeto, não todos os endpoints da API nem a disponibilidade atual. Os arquivos CSV brutos não estavam presentes para nova perfilagem. Todos os tipos de entrada são STRING, por decisão da bronze; os tipos analíticos são aplicados na silver.

## O que a implementação existente já documenta

- A silver registra colunas totalmente vazias em matches, incluindo temporada, estádio e atualização; em players registra nascimento, altura e peso vazios. Isso é evidência documentada da captura específica, não indisponibilidade universal da API.
- O H2H recebido inclui confrontos posteriores à partida consultada. O SQL mantém apenas jogos estritamente anteriores e exclui o próprio jogo.
- Os eventos dessa captura são gols, segundo o comentário do DDL; não extrapolar para cobertura comprovada de passes e cartões.
- As métricas do jogador são pós-jogo. Para previsão, agregá-las apenas sobre jogos anteriores.

Evidências: [matches](../../sql/02_silver/04_create_table_matches.sql), [players](../../sql/02_silver/03_create_table_players.sql), [H2H](../../sql/02_silver/06_create_table_h2h.sql), [estatísticas](../../sql/02_silver/10_create_table_player_match_stats.sql).

## stored_matches.csv

Fonte local: [01_create_external_table_stored_matches.sql](../../sql/01_bronze/01_create_external_table_stored_matches.sql).

| Campo exato no CSV | Tipo bronze | Significado |
|---|---|---|
| `is_finished` | `STRING` | Indicador exportado de encerramento. |
| `is_live` | `STRING` | Indicador exportado de jogo em andamento. |
| `starts_in_seconds` | `STRING` | Contagem relativa ao instante da exportação; não é histórico estável. |
| `status_enum` | `STRING` | Representação enumerada do status; redundante na captura documentada. |
| `id` | `STRING` | ID da entidade desta tabela na fonte. |
| `sport` | `STRING` | Modalidade esportiva. |
| `league` | `STRING` | Código ou referência da liga conforme exportação. |
| `season` | `STRING` | Temporada declarada no CSV; documentada como vazia na captura de matches. |
| `home_id` | `STRING` | ID do mandante. |
| `home_name` | `STRING` | Nome do mandante. |
| `home_short_name` | `STRING` | Nome curto do mandante. |
| `home_abbreviation` | `STRING` | Abreviatura do mandante. |
| `home_logo_url` | `STRING` | URL do escudo do mandante. |
| `home_flag_url` | `STRING` | URL da bandeira do mandante. |
| `away_id` | `STRING` | ID do visitante. |
| `away_name` | `STRING` | Nome do visitante. |
| `away_short_name` | `STRING` | Nome curto do visitante. |
| `away_abbreviation` | `STRING` | Abreviatura do visitante. |
| `away_logo_url` | `STRING` | URL do escudo do visitante. |
| `away_flag_url` | `STRING` | URL da bandeira do visitante. |
| `kickoff_utc` | `STRING` | Horário de início expresso em UTC. |
| `status` | `STRING` | Estado da partida publicado. |
| `score_home` | `STRING` | Placar do mandante exportado; distinguir regra do placar antes de normalizar. |
| `score_away` | `STRING` | Placar do visitante exportado; distinguir regra do placar antes de normalizar. |
| `linescore_home` | `STRING` | Detalhamento do placar por período do mandante; preservar representação original. |
| `linescore_away` | `STRING` | Detalhamento do placar por período do visitante; preservar representação original. |
| `attendance` | `STRING` | Público informado; classificação pagante/total não explicitada no DDL. |
| `broadcast` | `STRING` | Informação de transmissão no formato original. |
| `has_odds` | `STRING` | Indicador de existência de odds. |
| `venue` | `STRING` | Local declarado; vazio na captura documentada de matches. |
| `updated_at` | `STRING` | Atualização da fonte; vazia na captura documentada de matches. |
| `round` | `STRING` | Rodada publicada. |
| `winner` | `STRING` | Vencedor declarado; vazio na captura documentada. |
| `score` | `STRING` | Campo agregado de placar; vazio na captura documentada. |
| `linescore` | `STRING` | Campo agregado de placar por período; vazio na captura documentada. |

## teams.csv

Fonte local: [03_create_external_table_teams.sql](../../sql/01_bronze/03_create_external_table_teams.sql).

| Campo exato no CSV | Tipo bronze | Significado |
|---|---|---|
| `code` | `STRING` | Código da entidade na fonte. |
| `id` | `STRING` | ID da entidade desta tabela na fonte. |
| `name` | `STRING` | Nome principal publicado. |
| `short_name` | `STRING` | Nome curto. |
| `abbreviation` | `STRING` | Abreviatura. |
| `logo_url` | `STRING` | Endereço do escudo/imagem; licença separada. |
| `flag_url` | `STRING` | Endereço da bandeira/imagem. |
| `sport` | `STRING` | Modalidade esportiva. |
| `league` | `STRING` | Código ou referência da liga conforme exportação. |
| `country` | `STRING` | País na forma textual original. |
| `founded_year` | `STRING` | Ano de fundação. |
| `stats` | `STRING` | Conteúdo agregado de estatísticas no formato da exportação. |

## leagues.csv

Fonte local: [05_create_external_table_leagues.sql](../../sql/01_bronze/05_create_external_table_leagues.sql).

| Campo exato no CSV | Tipo bronze | Significado |
|---|---|---|
| `id` | `STRING` | ID da entidade desta tabela na fonte. |
| `name` | `STRING` | Nome principal publicado. |
| `sport` | `STRING` | Modalidade esportiva. |
| `country` | `STRING` | País na forma textual original. |

## players.csv

Fonte local: [07_create_external_table_players.sql](../../sql/01_bronze/07_create_external_table_players.sql).

| Campo exato no CSV | Tipo bronze | Significado |
|---|---|---|
| `id` | `STRING` | ID da entidade desta tabela na fonte. |
| `name` | `STRING` | Nome principal publicado. |
| `full_name` | `STRING` | Nome completo; vazio na captura documentada de players. |
| `display_name` | `STRING` | Nome de exibição; vazio na captura documentada de players. |
| `position` | `STRING` | Posição original; silver usa mapa de equivalências. |
| `jersey_number` | `STRING` | Camisa informada na exportação. |
| `headshot_url` | `STRING` | Imagem de perfil; direitos separados. |
| `nationality` | `STRING` | Nacionalidade no formato original. |
| `date_of_birth` | `STRING` | Nascimento; vazio na captura documentada de players. |
| `height` | `STRING` | Altura no formato original; vazia na captura documentada. |
| `height_cm` | `STRING` | Altura em centímetros; vazia na captura documentada. |
| `weight` | `STRING` | Peso no formato original; vazio na captura documentada. |
| `weight_kg` | `STRING` | Peso em quilogramas; vazio na captura documentada. |
| `team_id` | `STRING` | ID da equipe relacionada. |
| `team_name` | `STRING` | Nome da equipe relacionada. |
| `league_name` | `STRING` | Nome da liga relacionado ao registro. |
| `sport` | `STRING` | Modalidade esportiva. |

## stored_matches_h2h.csv

Fonte local: [09_create_external_table_stored_matches_h2h.sql](../../sql/01_bronze/09_create_external_table_stored_matches_h2h.sql).

| Campo exato no CSV | Tipo bronze | Significado |
|---|---|---|
| `for_match_id` | `STRING` | Partida para a qual o histórico H2H foi solicitado. |
| `match_id` | `STRING` | ID da partida descrita nesta linha. |
| `date` | `STRING` | Data do confronto histórico. |
| `home` | `STRING` | Nome do mandante no confronto. |
| `away` | `STRING` | Nome do visitante no confronto. |
| `home_score` | `STRING` | Placar do mandante no confronto. |
| `away_score` | `STRING` | Placar do visitante no confronto. |

## matches_weather.csv

Fonte local: [11_create_external_table_matches_weather.sql](../../sql/01_bronze/11_create_external_table_matches_weather.sql).

| Campo exato no CSV | Tipo bronze | Significado |
|---|---|---|
| `match_id` | `STRING` | ID da partida descrita nesta linha. |
| `kickoff_utc` | `STRING` | Horário de início expresso em UTC. |
| `venue_name` | `STRING` | Nome do local meteorológico associado à partida. |
| `latitude` | `STRING` | Latitude do local. |
| `longitude` | `STRING` | Longitude do local. |
| `roof` | `STRING` | Informação sobre cobertura/teto no formato original. |
| `temperature_c` | `STRING` | Temperatura em graus Celsius. |
| `apparent_temperature_c` | `STRING` | Sensação térmica em graus Celsius. |
| `relative_humidity_pct` | `STRING` | Umidade relativa em percentual. |
| `precipitation_mm` | `STRING` | Precipitação em milímetros; janela precisa ser confirmada. |
| `wind_kph` | `STRING` | Velocidade do vento em km/h. |
| `wind_gust_kph` | `STRING` | Rajada de vento em km/h. |
| `cloud_cover_pct` | `STRING` | Cobertura de nuvens em percentual. |
| `condition` | `STRING` | Condição meteorológica descrita. |

## matches_events.csv

Fonte local: [13_create_external_table_matches_events.sql](../../sql/01_bronze/13_create_external_table_matches_events.sql).

| Campo exato no CSV | Tipo bronze | Significado |
|---|---|---|
| `match_id` | `STRING` | ID da partida descrita nesta linha. |
| `team` | `STRING` | Referência de equipe no evento; não assumir que seja ID sem inspecionar o payload. |
| `player_name` | `STRING` | Nome do atleta principal. |
| `assist_name` | `STRING` | Nome de quem deu assistência quando presente. |
| `event_type` | `STRING` | Tipo de evento; o comentário local registra apenas Goal nesta captura. |
| `event_detail` | `STRING` | Detalhamento original do evento. |
| `elapsed` | `STRING` | Minuto do evento. |
| `elapsed_extra` | `STRING` | Minutos de acréscimo explícitos. |

## stored_matches_stats_players.csv

Fonte local: [15_create_external_table_stored_matches_stats_players.sql](../../sql/01_bronze/15_create_external_table_stored_matches_stats_players.sql).

| Campo exato no CSV | Tipo bronze | Significado |
|---|---|---|
| `match_id` | `STRING` | ID da partida descrita nesta linha. |
| `team_id` | `STRING` | ID da equipe relacionada. |
| `team_name` | `STRING` | Nome da equipe relacionada. |
| `player_id` | `STRING` | ID do atleta. |
| `player_name` | `STRING` | Nome do atleta principal. |
| `position` | `STRING` | Posição original; silver usa mapa de equivalências. |
| `jersey_number` | `STRING` | Camisa informada na exportação. |
| `stats_json` | `STRING` | JSON serializado de métricas por jogador; desdobrado na silver. |

## Caminhos JSON que a silver já desdobra

Além das colunas acima, `stats_json` contém os seguintes caminhos usados pelo SQL. O prefixo `$.` é relativo ao JSON desse campo; os tipos são os casts existentes, não inferências sobre toda resposta da API.

| Caminho JSON | Coluna silver | Tipo silver |
|---|---|---|
| `$.minutes.value` | `minutes` | `INT64` |
| `$.goals.value` | `goals` | `INT64` |
| `$.assists.value` | `assists` | `INT64` |
| `$.shots_total.value` | `shots_total` | `INT64` |
| `$.shots_on.value` | `shots_on` | `INT64` |
| `$.passes_total.value` | `passes_total` | `INT64` |
| `$.pass_accuracy.value` | `pass_accuracy` | `FLOAT64` |
| `$.yellow_cards.value` | `yellow_cards` | `INT64` |
| `$.red_cards.value` | `red_cards` | `INT64` |
| `$.rating.value` | `rating` | `FLOAT64` |
| `$.substitute.value` | `substitute` | `BOOL` |
