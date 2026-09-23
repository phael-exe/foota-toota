# Dicionário normalizado de futebol

Consulta: 2026-09-14. **336 campos em 32 entidades.**

Este é um modelo proposto para cruzar fontes. Os nomes e tipos abaixo são escolhas do Foota Toota, não promessas de campos presentes em cada fornecedor. O [catálogo](catalogo.md) indica quais entidades investigar em cada fonte; a existência da entidade não garante todos os seus campos.

As chaves são lógicas. Uma tabela de observações acrescenta `source_id` e `ingested_at` à chave do fato para preservar versões. A camada canônica resolve divergências com regras explícitas. Campos opcionais ausentes ficam nulos; chaves obrigatórias ausentes vão para quarentena. Para arrays, distinguir coleção vazia de informação ainda não coletada por um status de completude.

## Convenções para integrar

- IDs externos são texto e sempre acompanhados do fornecedor. O número 42 em duas APIs não identifica necessariamente a mesma pessoa.
- Usar UTC para instantes e manter o fuso IANA do local. Datas sem horário continuam DATE; não inventar meia-noite como publicação.
- Nome do clube não é chave. Equipes feminina, masculina, sub-20 e futsal precisam de IDs diferentes.
- Separar valor de mercado, taxa de transferência, salário e preço fantasy; moeda, data e condição de estimativa são essenciais.
- Percentual 55 e fração 0.55 só são convertidos quando a unidade original estiver documentada.
- xG é a qualidade estimada das chances segundo um modelo. Guardar fornecedor/versão; não misturar modelos como uma única medida.
- Placar de 90 minutos, gols só da prorrogação e disputa de pênaltis são componentes separados. Alguns feeds entregam totais acumulados; a transformação precisa documentar isso.
- Não juntar coordenadas de sistemas diferentes. Registrar origem, direção de ataque, dimensões e unidades antes da conversão.
- Estatísticas pós-jogo, anúncios futuros e odds observadas depois do corte não podem entrar numa previsão anterior. `first_seen_at` é a evidência conservadora de disponibilidade no pipeline; publicar hoje um fato antigo não o torna conhecido no passado.
- Notícias republicadas da mesma agência ou do mesmo anúncio são uma cadeia de origem, não várias confirmações independentes.

## Entidades

- [proveniencia](#proveniencia) — Proveniência comum a todos os registros.
- [competicao](#competicao) — Competições e edições.
- [equipe](#equipe) — Clubes e seleções.
- [jogador](#jogador) — Identidade do jogador.
- [elenco](#elenco) — Vínculos e inscrição no elenco.
- [partida](#partida) — Partidas.
- [classificacao](#classificacao) — Tabelas de classificação.
- [escalacao](#escalacao) — Escalações e participação.
- [evento](#evento) — Ações de jogo.
- [estatistica](#estatistica) — Métricas esportivas.
- [rastreamento](#rastreamento) — Tracking e contexto espacial.
- [transferencia](#transferencia) — Movimentações de atletas.
- [valor_mercado](#valor_mercado) — Avaliação de mercado.
- [registro](#registro) — Registros federativos.
- [noticia](#noticia) — Notícias e evidências editoriais.
- [indisponibilidade](#indisponibilidade) — Lesões e outras ausências.
- [sancao](#sancao) — Suspensões e decisões disciplinares.
- [arbitro](#arbitro) — Árbitros e nomeações.
- [estadio](#estadio) — Estádios e locais.
- [clima](#clima) — Clima no local de jogo.
- [bilheteria](#bilheteria) — Público e borderôs.
- [odd](#odd) — Cotações.
- [rating](#rating) — Índices de força.
- [previsao](#previsao) — Previsões esportivas.
- [fantasy](#fantasy) — Fantasy games.
- [salario](#salario) — Salários publicados.
- [financas_clube](#financas_clube) — Finanças de clubes.
- [relatorio_mercado](#relatorio_mercado) — Mercado agregado e demografia.
- [midia](#midia) — Fotos, vídeos e metadados.
- [transmissao](#transmissao) — Programação de transmissão.
- [documento](#documento) — Documentos e regulamentos.
- [identificador](#identificador) — Conciliação de IDs.

<a id="proveniencia"></a>
## proveniencia — Proveniência comum a todos os registros

**Granularidade:** Uma observação coletada de uma fonte.

**Chave lógica:** `source_id, source_record_id, ingested_at`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `source_id` | `STRING` | Identificador da fonte no catálogo; não é segredo | ID |
| `source_record_id` | `STRING` | Identificador original; usar chave composta documentada quando não houver ID | ID |
| `source_url` | `STRING` | URL da evidência ou endpoint sem credenciais | URL |
| `source_updated_at` | `TIMESTAMP` | Última atualização declarada pelo fornecedor, se informada | UTC |
| `published_at` | `TIMESTAMP` | Momento original de publicação, quando conhecido | UTC |
| `first_seen_at` | `TIMESTAMP` | Primeiro instante em que nosso sistema observou a informação | UTC |
| `ingested_at` | `TIMESTAMP` | Instante de chegada ao pipeline | UTC |
| `valid_from` | `TIMESTAMP` | Início da validade do fato no mundo real, quando conhecido | UTC |
| `valid_to` | `TIMESTAMP` | Fim da validade; nulo para intervalo ainda aberto | UTC |
| `schema_version` | `STRING` | Versão do contrato de transformação usado | texto |
| `raw_payload_ref` | `STRING` | Referência interna ao dado bruto preservado | URI |
| `license_ref` | `STRING` | Referência aos termos aplicáveis à captura e ao uso | URL/texto |
| `quality_status` | `STRING` | Situação da validação: accepted, quarantined ou pending | enum |

<a id="competicao"></a>
## competicao — Competições e edições

**Granularidade:** Uma edição de competição com categoria e temporada.

**Chave lógica:** `competition_id, season_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `competition_id` | `STRING` | ID interno estável da competição | ID |
| `season_id` | `STRING` | ID interno da edição; não inferir apenas pelo mês do jogo | ID |
| `name` | `STRING` | Nome oficial ou nome preferencial documentado | texto |
| `country_code` | `STRING` | País principal; nulo para competição multinacional | ISO 3166-1 alpha-2 |
| `confederation` | `STRING` | Confederação responsável, se aplicável | texto |
| `season_label` | `STRING` | Rótulo da edição, como 2025/26 ou 2026 | texto |
| `starts_on` | `DATE` | Primeiro dia da edição | data |
| `ends_on` | `DATE` | Último dia da edição | data |
| `gender_category` | `STRING` | Categoria declarada pela competição | texto |
| `age_category` | `STRING` | Categoria etária: sênior, sub-20 etc. | texto |
| `discipline` | `STRING` | Futebol de campo, futsal ou futebol de areia | enum |
| `tier` | `INT64` | Nível da divisão nacional quando aplicável | ordinal |

<a id="equipe"></a>
## equipe — Clubes e seleções

**Granularidade:** Uma equipe esportiva; categorias separadas.

**Chave lógica:** `team_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `team_id` | `STRING` | ID interno da equipe | ID |
| `organization_id` | `STRING` | Organização que pode manter equipes de várias categorias | ID |
| `name` | `STRING` | Nome de exibição da equipe | texto |
| `short_name` | `STRING` | Nome curto ou sigla | texto |
| `country_code` | `STRING` | País de representação ou sede | ISO 3166-1 alpha-2 |
| `team_type` | `STRING` | Club ou national_team | enum |
| `gender_category` | `STRING` | Categoria da equipe | texto |
| `age_category` | `STRING` | Categoria etária | texto |
| `founded_on` | `DATE` | Fundação; não inventar dia/mês se só o ano for conhecido | data |
| `stadium_id` | `STRING` | Estádio habitual; não implica mando de todos os jogos | ID |
| `website` | `STRING` | Site oficial | URL |

<a id="jogador"></a>
## jogador — Identidade do jogador

**Granularidade:** Uma pessoa; vínculo com clube fica no elenco.

**Chave lógica:** `player_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `player_id` | `STRING` | ID interno estável da pessoa | ID |
| `full_name` | `STRING` | Nome completo publicado | texto |
| `display_name` | `STRING` | Nome usado em escalações e interface | texto |
| `birth_date` | `DATE` | Data de nascimento publicada | data |
| `nationalities` | `ARRAY<STRING>` | Nacionalidades declaradas; podem ser múltiplas | ISO 3166-1 alpha-2 |
| `birth_country` | `STRING` | País de nascimento, distinto de nacionalidade | ISO 3166-1 alpha-2 |
| `height_cm` | `FLOAT64` | Altura normalizada | cm |
| `weight_kg` | `FLOAT64` | Peso informado e datado quando possível | kg |
| `preferred_foot` | `STRING` | Pé preferido: left, right, both ou unknown | enum |
| `primary_position` | `STRING` | Posição principal normalizada com tabela de equivalência | enum |

<a id="elenco"></a>
## elenco — Vínculos e inscrição no elenco

**Granularidade:** Jogador, equipe e intervalo de vínculo.

**Chave lógica:** `player_id, team_id, valid_from`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `player_id` | `STRING` | Atleta vinculado | ID |
| `team_id` | `STRING` | Equipe do vínculo | ID |
| `competition_id` | `STRING` | Competição da inscrição quando específica | ID |
| `season_id` | `STRING` | Edição de referência | ID |
| `jersey_number` | `INT64` | Número usado nesse vínculo/temporada | número |
| `contract_start` | `DATE` | Início do contrato quando publicado | data |
| `contract_end` | `DATE` | Fim do contrato divulgado, sem inferir renovação | data |
| `on_loan` | `BOOL` | Se o vínculo com a equipe é por empréstimo | booleano |
| `parent_team_id` | `STRING` | Equipe detentora do vínculo de origem se publicada | ID |

<a id="partida"></a>
## partida — Partidas

**Granularidade:** Uma partida, com versões de observação.

**Chave lógica:** `match_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `match_id` | `STRING` | ID interno estável; não muda em reagendamento | ID |
| `competition_id` | `STRING` | Competição da partida | ID |
| `season_id` | `STRING` | Edição da competição | ID |
| `home_team_id` | `STRING` | Equipe designada mandante | ID |
| `away_team_id` | `STRING` | Equipe designada visitante | ID |
| `kickoff_utc` | `TIMESTAMP` | Horário previsto/confirmado com histórico de revisões | UTC |
| `stadium_id` | `STRING` | Local efetivo do jogo | ID |
| `neutral_venue` | `BOOL` | Indica campo neutro; distinto de mandante administrativo | booleano |
| `stage` | `STRING` | Fase do torneio | texto |
| `round` | `STRING` | Rodada ou etapa; pode não ser número | texto |
| `leg` | `INT64` | Perna da eliminatória, se aplicável | ordinal |
| `status` | `STRING` | scheduled, live, halftime, finished, postponed, cancelled, abandoned ou unknown | enum |
| `home_score_90` | `INT64` | Gols do mandante até o fim do tempo regulamentar com acréscimos | gols |
| `away_score_90` | `INT64` | Gols do visitante no tempo regulamentar com acréscimos | gols |
| `home_score_et` | `INT64` | Gols adicionais do mandante só na prorrogação | gols |
| `away_score_et` | `INT64` | Gols adicionais do visitante só na prorrogação | gols |
| `home_penalties` | `INT64` | Cobranças convertidas pelo mandante na disputa de pênaltis | gols |
| `away_penalties` | `INT64` | Cobranças convertidas pelo visitante na disputa de pênaltis | gols |
| `winner_team_id` | `STRING` | Vencedor do jogo conforme regra; nulo em empate | ID |
| `qualified_team_id` | `STRING` | Equipe que avançou na eliminatória; pode não vencer este jogo | ID |
| `attendance` | `INT64` | Público publicado; definição deve ser preservada | pessoas |

<a id="classificacao"></a>
## classificacao — Tabelas de classificação

**Granularidade:** Equipe, grupo, edição e instante da tabela.

**Chave lógica:** `competition_id, season_id, group_id, team_id, as_of`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `competition_id` | `STRING` | Competição | ID |
| `season_id` | `STRING` | Edição | ID |
| `group_id` | `STRING` | Grupo/fase; usar valor explícito único para tabela geral | ID |
| `team_id` | `STRING` | Equipe classificada | ID |
| `as_of` | `TIMESTAMP` | Instante ao qual a tabela se refere | UTC |
| `rank` | `INT64` | Posição na tabela | ordinal |
| `played` | `INT64` | Partidas consideradas na classificação | jogos |
| `wins` | `INT64` | Vitórias consideradas | jogos |
| `draws` | `INT64` | Empates considerados | jogos |
| `losses` | `INT64` | Derrotas consideradas | jogos |
| `goals_for` | `INT64` | Gols pró considerados | gols |
| `goals_against` | `INT64` | Gols contra considerados | gols |
| `points` | `NUMERIC` | Pontos oficiais incluindo decisões administrativas | pontos |
| `points_adjustment` | `NUMERIC` | Ajuste administrativo quando explicitamente informado | pontos |

<a id="escalacao"></a>
## escalacao — Escalações e participação

**Granularidade:** Um jogador em uma partida.

**Chave lógica:** `match_id, team_id, player_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `match_id` | `STRING` | Partida | ID |
| `team_id` | `STRING` | Equipe na partida | ID |
| `player_id` | `STRING` | Jogador | ID |
| `lineup_status` | `STRING` | Predicted, confirmed ou revised | enum |
| `is_starter` | `BOOL` | Se entrou como titular | booleano |
| `is_captain` | `BOOL` | Se capitão nessa escalação | booleano |
| `position` | `STRING` | Posição exercida no jogo | texto |
| `jersey_number` | `INT64` | Camisa nessa partida | número |
| `formation` | `STRING` | Esquema tático declarado para a equipe | texto |
| `minutes_played` | `FLOAT64` | Tempo jogado conforme definição do fornecedor | minutos |

<a id="evento"></a>
## evento — Ações de jogo

**Granularidade:** Uma ação/evento com possibilidade de revisão.

**Chave lógica:** `event_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `event_id` | `STRING` | ID interno; preservar o original na proveniência | ID |
| `match_id` | `STRING` | Partida | ID |
| `sequence` | `INT64` | Ordem dentro do feed | ordinal |
| `period` | `STRING` | 1H, 2H, ET1, ET2 ou PSO | enum |
| `minute` | `INT64` | Minuto exibido no relógio do jogo | minutos |
| `added_minute` | `INT64` | Acréscimo explícito, como 2 em 45+2 | minutos |
| `elapsed_seconds` | `FLOAT64` | Segundos desde o início do período definido | segundos |
| `team_id` | `STRING` | Equipe associada à ação | ID |
| `player_id` | `STRING` | Atleta principal; pode ser desconhecido | ID |
| `related_player_id` | `STRING` | Outro atleta, com papel definido no qualifier | ID |
| `event_type` | `STRING` | Goal, pass, shot, foul, card, substitution etc. | enum |
| `outcome` | `STRING` | Resultado da ação segundo o modelo de eventos | texto |
| `x` | `FLOAT64` | Coordenada longitudinal, no sistema declarado | unidade do sistema |
| `y` | `FLOAT64` | Coordenada transversal, no sistema declarado | unidade do sistema |
| `coordinate_system` | `STRING` | Origem, dimensão e orientação do campo; obrigatório se x/y preenchidos | texto |
| `qualifiers` | `JSON` | Detalhes específicos, preservando semântica do provedor | objeto |
| `is_cancelled` | `BOOL` | Ação anulada/corrigida; preservar histórico | booleano |

<a id="estatistica"></a>
## estatistica — Métricas esportivas

**Granularidade:** Uma métrica por sujeito, escopo e janela.

**Chave lógica:** `metric_record_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `metric_record_id` | `STRING` | ID interno da observação estatística | ID |
| `subject_type` | `STRING` | Player ou team | enum |
| `subject_id` | `STRING` | ID do jogador ou equipe | ID |
| `scope_type` | `STRING` | Match, season, competition ou rolling_window | enum |
| `scope_id` | `STRING` | Partida/temporada/janela relacionada | ID |
| `metric_name` | `STRING` | Código como goals, shots_total, passes_completed, xg ou rating | texto |
| `value` | `FLOAT64` | Valor numérico; nulo quando ausente, nunca zero artificial | unidade declarada |
| `unit` | `STRING` | Count, fraction, percent, goals, metres etc. | texto |
| `aggregation` | `STRING` | Sum, mean, per90, rate, maximum etc. | enum |
| `denominator` | `FLOAT64` | Base do cálculo, se for taxa/média | unidade da base |
| `period` | `STRING` | Partida inteira, primeiro tempo, janela etc. | texto |
| `model_version` | `STRING` | Fornecedor e versão para xG, notas e outras métricas derivadas | texto |

<a id="rastreamento"></a>
## rastreamento — Tracking e contexto espacial

**Granularidade:** Uma entidade observada num frame/amostra.

**Chave lógica:** `match_id, frame_id, tracked_object_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `match_id` | `STRING` | Partida | ID |
| `frame_id` | `STRING` | Identificador de frame ou amostra | ID |
| `tracked_object_id` | `STRING` | Objeto rastreado; pode ser anônimo | ID |
| `player_id` | `STRING` | Atleta resolvido; nulo quando anônimo ou bola | ID |
| `object_type` | `STRING` | Player, ball ou referee | enum |
| `period` | `STRING` | Período de jogo | enum |
| `timestamp_seconds` | `FLOAT64` | Tempo em relação ao início declarado do período/vídeo | segundos |
| `x` | `FLOAT64` | Coordenada longitudinal no sistema original | unidade declarada |
| `y` | `FLOAT64` | Coordenada transversal no sistema original | unidade declarada |
| `z` | `FLOAT64` | Altura quando disponível | unidade declarada |
| `coordinate_system` | `STRING` | Dimensões, origem, orientação e unidade | texto |
| `sample_rate_hz` | `FLOAT64` | Frequência nominal da captura quando conhecida | Hz |
| `is_observed` | `BOOL` | Distingue observação direta de posição inferida quando informado | booleano |
| `event_id` | `STRING` | Evento associado a freeze-frame; não implica sequência contínua | ID |

<a id="transferencia"></a>
## transferencia — Movimentações de atletas

**Granularidade:** Uma movimentação com versões de confirmação.

**Chave lógica:** `transfer_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `transfer_id` | `STRING` | ID interno da movimentação | ID |
| `player_id` | `STRING` | Atleta | ID |
| `from_team_id` | `STRING` | Origem; nulo se desconhecida ou sem clube | ID |
| `to_team_id` | `STRING` | Destino; nulo para saída sem destino conhecido | ID |
| `transfer_type` | `STRING` | Permanent, loan, loan_return, free, release ou unknown | enum |
| `status` | `STRING` | Rumour, reported, announced, registered, completed, cancelled ou denied | enum |
| `announced_at` | `TIMESTAMP` | Quando o anúncio foi publicado | UTC |
| `effective_on` | `DATE` | Quando o vínculo passa a valer | data |
| `fee_amount` | `NUMERIC` | Taxa publicada; nulo para valor não divulgado | moeda declarada |
| `fee_currency` | `STRING` | Moeda da taxa publicada | ISO 4217 |
| `fee_status` | `STRING` | Confirmed, reported, estimated, undisclosed ou free | enum |
| `add_ons_amount` | `NUMERIC` | Bônus condicionais separados da parcela fixa | moeda declarada |
| `loan_end_on` | `DATE` | Fim previsto de empréstimo quando publicado | data |
| `evidence_article_id` | `STRING` | Notícia/documento que fundamenta esse status | ID |

<a id="valor_mercado"></a>
## valor_mercado — Avaliação de mercado

**Granularidade:** Uma estimativa de valor por atleta e data.

**Chave lógica:** `player_id, valuation_date, source_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `player_id` | `STRING` | Atleta avaliado | ID |
| `valuation_date` | `DATE` | Data da avaliação, não da coleta | data |
| `amount` | `NUMERIC` | Valor estimado | moeda declarada |
| `currency` | `STRING` | Moeda da estimativa | ISO 4217 |
| `method` | `STRING` | Comunidade, modelo estatístico ou outra metodologia publicada | texto |
| `model_version` | `STRING` | Versão do modelo, se divulgada | texto |

<a id="registro"></a>
## registro — Registros federativos

**Granularidade:** Uma publicação de registro/movimentação.

**Chave lógica:** `registration_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `registration_id` | `STRING` | ID interno do registro/publicação | ID |
| `player_id` | `STRING` | Atleta identificado | ID |
| `team_id` | `STRING` | Clube identificado na publicação | ID |
| `federation` | `STRING` | Entidade responsável | texto |
| `registration_number` | `STRING` | Número esportivo publicado, quando necessário para conciliação | ID |
| `registration_type` | `STRING` | Tipo de movimentação exatamente definido na fonte | texto |
| `publication_date` | `DATE` | Data do boletim/publicação | data |
| `effective_on` | `DATE` | Data de efeito, apenas se explicitada | data |
| `document_id` | `STRING` | Referência ao boletim de origem | ID |

<a id="noticia"></a>
## noticia — Notícias e evidências editoriais

**Granularidade:** Uma matéria por publicador e URL canônica.

**Chave lógica:** `article_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `article_id` | `STRING` | ID interno da matéria | ID |
| `canonical_url` | `STRING` | URL canônica sem rastreadores | URL |
| `publisher` | `STRING` | Redação/agência original | texto |
| `aggregator` | `STRING` | Serviço que entregou a matéria, se diferente | texto |
| `title` | `STRING` | Título autorizado para armazenamento/exibição | texto |
| `summary` | `STRING` | Resumo autorizado ou elaborado com proveniência | texto |
| `author` | `STRING` | Autoria pública quando informada | texto |
| `language` | `STRING` | Idioma do conteúdo | BCP 47 |
| `published_at` | `TIMESTAMP` | Hora original da publicação, se conhecida | UTC |
| `updated_at` | `TIMESTAMP` | Hora da revisão editorial, se conhecida | UTC |
| `topic` | `STRING` | Match, transfer, injury, finance, disciplinary etc. | enum |
| `claim_status` | `STRING` | Reported, rumour, confirmed, denied ou unknown; por alegação quando necessário | enum |
| `entity_mentions` | `JSON` | Menções e vínculos com jogadores/equipes; incluir confiança da resolução | objeto |
| `story_cluster_id` | `STRING` | Agrupamento de republicações e matérias sobre o mesmo fato | ID |
| `original_source_url` | `STRING` | Link da apuração ou anúncio primário, quando localizado | URL |

<a id="indisponibilidade"></a>
## indisponibilidade — Lesões e outras ausências

**Granularidade:** Relato de indisponibilidade de jogador com validade temporal.

**Chave lógica:** `availability_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `availability_id` | `STRING` | ID interno da observação | ID |
| `player_id` | `STRING` | Atleta | ID |
| `team_id` | `STRING` | Equipe no momento do relato | ID |
| `match_id` | `STRING` | Partida relacionada, quando específico | ID |
| `reason` | `STRING` | Motivo publicado; não inferir diagnóstico | texto |
| `availability_status` | `STRING` | Out, doubtful, available ou unknown | enum |
| `reported_on` | `DATE` | Data do boletim/relato | data |
| `expected_return_on` | `DATE` | Retorno previsto, não garantido | data |
| `confirmed_return_on` | `DATE` | Retorno confirmado quando observado | data |
| `evidence_article_id` | `STRING` | Boletim/notícia que fundamenta a informação | ID |

<a id="sancao"></a>
## sancao — Suspensões e decisões disciplinares

**Granularidade:** Uma decisão ou revisão publicada.

**Chave lógica:** `sanction_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `sanction_id` | `STRING` | ID interno da decisão | ID |
| `subject_type` | `STRING` | Player, team, coach ou official | enum |
| `subject_id` | `STRING` | Entidade envolvida | ID |
| `competition_id` | `STRING` | Competição em que vale a decisão, se explícita | ID |
| `decision_date` | `DATE` | Data da decisão | data |
| `matches_suspended` | `INT64` | Número de jogos de suspensão informado | jogos |
| `status` | `STRING` | Issued, appealed, stayed, served, overturned ou unknown | enum |
| `document_id` | `STRING` | Documento da decisão; não apenas manchete | ID |

<a id="arbitro"></a>
## arbitro — Árbitros e nomeações

**Granularidade:** Uma nomeação por árbitro, jogo e função.

**Chave lógica:** `match_id, referee_id, role`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `referee_id` | `STRING` | ID interno da pessoa | ID |
| `name` | `STRING` | Nome publicado | texto |
| `country_code` | `STRING` | País/federação representada quando informado | ISO 3166-1 alpha-2 |
| `match_id` | `STRING` | Partida da nomeação | ID |
| `role` | `STRING` | Main, assistant, fourth, VAR, AVAR etc. | enum |
| `appointment_status` | `STRING` | Appointed, replaced ou confirmed | enum |

<a id="estadio"></a>
## estadio — Estádios e locais

**Granularidade:** Um local físico.

**Chave lógica:** `stadium_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `stadium_id` | `STRING` | ID interno do local | ID |
| `name` | `STRING` | Nome do estádio ou campo | texto |
| `city` | `STRING` | Município | texto |
| `country_code` | `STRING` | País | ISO 3166-1 alpha-2 |
| `latitude` | `FLOAT64` | Latitude do local | graus WGS84 |
| `longitude` | `FLOAT64` | Longitude do local | graus WGS84 |
| `timezone` | `STRING` | Fuso geográfico; não apenas deslocamento fixo | IANA |
| `capacity` | `INT64` | Capacidade publicada com validade temporal | pessoas |
| `surface` | `STRING` | Natural, artificial, hybrid ou unknown | enum |
| `altitude_m` | `FLOAT64` | Altitude quando obtida de fonte adequada | m |

<a id="clima"></a>
## clima — Clima no local de jogo

**Granularidade:** Uma variável meteorológica por local, horário e emissão.

**Chave lógica:** `weather_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `weather_id` | `STRING` | ID interno da amostra | ID |
| `match_id` | `STRING` | Partida associada, se houver | ID |
| `stadium_id` | `STRING` | Local da consulta | ID |
| `valid_at` | `TIMESTAMP` | Horário ao qual a condição se refere | UTC |
| `issued_at` | `TIMESTAMP` | Momento de emissão do modelo/previsão quando conhecido | UTC |
| `data_kind` | `STRING` | Forecast, observation ou reanalysis | enum |
| `temperature_c` | `FLOAT64` | Temperatura do ar | °C |
| `humidity_pct` | `FLOAT64` | Umidade relativa | percentual 0–100 |
| `precipitation_mm` | `FLOAT64` | Acumulado no intervalo declarado | mm |
| `wind_kph` | `FLOAT64` | Velocidade do vento | km/h |
| `interval_minutes` | `INT64` | Janela temporal da medida/acumulado | minutos |

<a id="bilheteria"></a>
## bilheteria — Público e borderôs

**Granularidade:** Um boletim financeiro de jogo e versão.

**Chave lógica:** `match_id, document_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `match_id` | `STRING` | Partida | ID |
| `document_id` | `STRING` | Boletim financeiro de origem | ID |
| `paid_attendance` | `INT64` | Público pagante segundo o documento | pessoas |
| `total_attendance` | `INT64` | Público total segundo o documento | pessoas |
| `gross_revenue` | `NUMERIC` | Receita bruta de bilheteria | moeda declarada |
| `expenses` | `NUMERIC` | Despesas discriminadas ou total publicadas | moeda declarada |
| `net_revenue` | `NUMERIC` | Receita líquida do evento publicada | moeda declarada |
| `currency` | `STRING` | Moeda do boletim | ISO 4217 |

<a id="odd"></a>
## odd — Cotações

**Granularidade:** Uma seleção, mercado, casa e instante.

**Chave lógica:** `quote_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `quote_id` | `STRING` | ID interno da cotação observada | ID |
| `match_id` | `STRING` | Evento esportivo resolvido | ID |
| `bookmaker` | `STRING` | Casa ou exchange | texto |
| `market` | `STRING` | 1X2, totals, spread, both_teams_score, player_prop etc. | enum |
| `period` | `STRING` | 90min, first_half, including_et ou outra definição explícita | texto |
| `selection` | `STRING` | Home, draw, away, over, under ou seleção do mercado | texto |
| `line` | `NUMERIC` | Linha do mercado quando houver, como total 2.5 | unidade do mercado |
| `decimal_odds` | `NUMERIC` | Cotação convertida ao formato decimal | razão > 1 |
| `quoted_at` | `TIMESTAMP` | Hora informada pelo fornecedor para a cotação | UTC |
| `observed_at` | `TIMESTAMP` | Quando a cotação foi observada pelo nosso sistema | UTC |
| `is_live` | `BOOL` | Se cotação foi oferecida durante o jogo | booleano |
| `side` | `STRING` | Back, lay ou bookmaker | enum |
| `volume` | `NUMERIC` | Volume informado, com moeda e definição se houver | moeda declarada |

<a id="rating"></a>
## rating — Índices de força

**Granularidade:** Um índice de equipe/jogador numa data.

**Chave lógica:** `subject_id, rating_system, as_of`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `subject_id` | `STRING` | Equipe ou atleta avaliado | ID |
| `rating_system` | `STRING` | Elo, SPI, UEFA_coefficient ou outro sistema | texto |
| `rating_value` | `FLOAT64` | Valor na escala original | escala do modelo |
| `rank` | `INT64` | Posição no universo avaliado | ordinal |
| `as_of` | `TIMESTAMP` | Momento ao qual o índice se refere | UTC |
| `model_version` | `STRING` | Metodologia/versão identificável | texto |

<a id="previsao"></a>
## previsao — Previsões esportivas

**Granularidade:** Uma previsão por modelo, partida e emissão.

**Chave lógica:** `match_id, model_version, issued_at`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `match_id` | `STRING` | Partida prevista | ID |
| `model_version` | `STRING` | Modelo e versão; distinguir fornecedor e modelo próprio | texto |
| `issued_at` | `TIMESTAMP` | Momento de geração da previsão | UTC |
| `prediction_horizon` | `STRING` | Resultado em 90min, classificação ou outro alvo explícito | texto |
| `home_win_probability` | `FLOAT64` | Probabilidade de vitória do mandante no alvo escolhido | fração 0–1 |
| `draw_probability` | `FLOAT64` | Probabilidade de empate; nulo se alvo não admite empate | fração 0–1 |
| `away_win_probability` | `FLOAT64` | Probabilidade de vitória do visitante no alvo escolhido | fração 0–1 |
| `expected_home_goals` | `FLOAT64` | Gols esperados pelo modelo antes da partida | gols |
| `expected_away_goals` | `FLOAT64` | Gols esperados pelo modelo antes da partida | gols |

<a id="fantasy"></a>
## fantasy — Fantasy games

**Granularidade:** Atleta, jogo fantasy, temporada e rodada.

**Chave lógica:** `game_name, season_id, round, player_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `game_name` | `STRING` | FPL, Cartola ou outro produto | texto |
| `season_id` | `STRING` | Temporada do fantasy | ID |
| `round` | `STRING` | Rodada/deadline do produto, distinta da rodada física em jogos adiados | texto |
| `player_id` | `STRING` | Atleta resolvido | ID |
| `fantasy_player_id` | `STRING` | ID original do atleta nessa edição do fantasy | ID |
| `price` | `NUMERIC` | Preço normalizado após verificar escala original | moeda virtual |
| `points` | `FLOAT64` | Pontos segundo as regras vigentes | pontos fantasy |
| `selected_pct` | `FLOAT64` | Porcentagem de escalação, quando publicada | percentual 0–100 |
| `status` | `STRING` | Status no jogo fantasy; não diagnóstico clínico | texto |
| `deadline_at` | `TIMESTAMP` | Fechamento do mercado/escalação | UTC |
| `rules_version` | `STRING` | Edição das regras e pesos de scouts | texto |

<a id="salario"></a>
## salario — Salários publicados

**Granularidade:** Atleta, clube, temporada e fonte da estimativa.

**Chave lógica:** `player_id, team_id, season_id, source_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `player_id` | `STRING` | Atleta | ID |
| `team_id` | `STRING` | Clube pagador | ID |
| `season_id` | `STRING` | Temporada de referência | ID |
| `amount` | `NUMERIC` | Salário divulgado ou estimado | moeda declarada |
| `currency` | `STRING` | Moeda | ISO 4217 |
| `pay_period` | `STRING` | Weekly, monthly ou annual | enum |
| `gross_or_net` | `STRING` | Gross, net ou unknown | enum |
| `includes_bonuses` | `BOOL` | Se inclui bônus; nulo quando desconhecido | booleano |
| `estimate_status` | `STRING` | Confirmed, reported, estimated ou unknown | enum |

<a id="financas_clube"></a>
## financas_clube — Finanças de clubes

**Granularidade:** Uma rubrica por clube e período contábil.

**Chave lógica:** `team_id, period_end, metric_name, source_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `team_id` | `STRING` | Clube ou entidade contábil | ID |
| `period_start` | `DATE` | Início do período contábil | data |
| `period_end` | `DATE` | Fim do período contábil; não presumir temporada esportiva | data |
| `metric_name` | `STRING` | Revenue, broadcast_revenue, matchday_revenue, commercial_revenue etc. | texto |
| `amount` | `NUMERIC` | Valor da rubrica com escala normalizada | moeda declarada |
| `currency` | `STRING` | Moeda original | ISO 4217 |
| `accounting_scope` | `STRING` | Entidade consolidada, clube, SAF ou outro perímetro | texto |
| `document_id` | `STRING` | Relatório de origem e edição | ID |

<a id="relatorio_mercado"></a>
## relatorio_mercado — Mercado agregado e demografia

**Granularidade:** Uma medida por período e recorte de relatório.

**Chave lógica:** `report_id, metric_name, segment`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `report_id` | `STRING` | Relatório de origem | ID |
| `period_start` | `DATE` | Início do período analisado | data |
| `period_end` | `DATE` | Fim do período analisado | data |
| `segment` | `STRING` | País, liga, gênero, faixa etária ou outro recorte explicitado | texto |
| `metric_name` | `STRING` | Transfer_count, total_fees, average_age etc. | texto |
| `value` | `NUMERIC` | Valor reportado | unidade declarada |
| `unit` | `STRING` | Pessoas, transferências, anos, moeda etc. | texto |
| `methodology` | `STRING` | Definição do universo e critérios do relatório | texto |

<a id="midia"></a>
## midia — Fotos, vídeos e metadados

**Granularidade:** Um item de mídia.

**Chave lógica:** `media_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `media_id` | `STRING` | ID interno da mídia | ID |
| `media_type` | `STRING` | Image, video, audio ou embed | enum |
| `title` | `STRING` | Título/descrição autorizada | texto |
| `publisher` | `STRING` | Canal, agência ou autor responsável | texto |
| `published_at` | `TIMESTAMP` | Publicação | UTC |
| `source_page_url` | `STRING` | Página original do item | URL |
| `embed_url` | `STRING` | Endereço de incorporação quando permitido | URL |
| `thumbnail_url` | `STRING` | Miniatura com condições de uso próprias | URL |
| `creator` | `STRING` | Autor/crédito público | texto |
| `license_name` | `STRING` | Licença específica do item | texto |
| `attribution_text` | `STRING` | Crédito exigido pelo detentor | texto |

<a id="transmissao"></a>
## transmissao — Programação de transmissão

**Granularidade:** Jogo, distribuidor e território.

**Chave lógica:** `match_id, broadcaster, territory`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `match_id` | `STRING` | Partida | ID |
| `broadcaster` | `STRING` | Canal ou plataforma | texto |
| `territory` | `STRING` | País/região onde a disponibilidade foi publicada | texto |
| `starts_at` | `TIMESTAMP` | Início da transmissão, distinto do kickoff | UTC |
| `access_type` | `STRING` | Free, subscription, pay_per_view ou unknown | enum |
| `listing_url` | `STRING` | Página que comprova a grade | URL |

<a id="documento"></a>
## documento — Documentos e regulamentos

**Granularidade:** Um documento e sua versão.

**Chave lógica:** `document_id, version`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `document_id` | `STRING` | ID interno do documento | ID |
| `document_type` | `STRING` | Match_report, regulation, financial_report, decision etc. | enum |
| `title` | `STRING` | Título da publicação | texto |
| `issuer` | `STRING` | Entidade emissora | texto |
| `published_on` | `DATE` | Data de publicação | data |
| `version` | `STRING` | Versão, revisão ou hash do arquivo | texto |
| `url` | `STRING` | Local de obtenção | URL |
| `related_entity_ids` | `JSON` | Jogos, atletas, equipes ou competições relacionados | objeto |

<a id="identificador"></a>
## identificador — Conciliação de IDs

**Granularidade:** Um vínculo de ID externo a entidade interna.

**Chave lógica:** `source_id, entity_type, external_id`.

| Campo | Tipo sugerido | Significado | Unidade |
|---|---|---|---|
| `source_id` | `STRING` | Fornecedor dono do identificador externo | ID |
| `entity_type` | `STRING` | Player, team, match, competition ou stadium | enum |
| `external_id` | `STRING` | ID externo preservado como texto | ID |
| `internal_id` | `STRING` | ID canônico do Foota Toota | ID |
| `match_method` | `STRING` | Exact_external_id, manual, composite ou probabilistic | enum |
| `match_confidence` | `FLOAT64` | Confiança interna de conciliação; não probabilidade universal | fração 0–1 |
| `reviewed` | `BOOL` | Se o vínculo foi revisado | booleano |
