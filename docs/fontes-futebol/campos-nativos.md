# Campos nativos selecionados

**75 campos em 7 fontes externas**, além das [105 colunas dos oito CSVs locais](dicionario-bigballs-csv.md).

Recortes de recursos documentados ou arquivos públicos observados. Não é um schema exaustivo de todos os endpoints. `[]` representa elementos de uma lista. Tipos nativos não determinam nulabilidade de todos os planos/versões. O destino é uma sugestão de transformação: IDs precisam de conciliação; nomes de países precisam de conversão; enums e datas precisam de parsers.

As demais fontes têm dicionário conceitual e referência na respectiva ficha. Um site HTML não expõe necessariamente um contrato estável de colunas; fornecedores profissionais podem exigir contrato para liberar o schema. Nenhum campo não observado foi marcado como confirmado.

## football-data.org

Objeto Match v4; campos selecionados.

Evidência: [documentação/arquivo original](https://docs.football-data.org/general/v4/match.html).

| Campo nativo | Tipo | Significado | Destino sugerido |
|---|---|---|---|
| `id` | integer | ID do jogo | `partida.match_id` |
| `utcDate` | string datetime | Início em UTC | `partida.kickoff_utc` |
| `status` | string | Estado original | `partida.status` |
| `competition.id` | integer | Competição | `partida.competition_id` |
| `season.id` | integer | Edição | `partida.season_id` |
| `homeTeam.id` | integer | Mandante | `partida.home_team_id` |
| `awayTeam.id` | integer | Visitante | `partida.away_team_id` |
| `matchday` | integer | Rodada | `partida.round` |
| `stage` | string | Fase | `partida.stage` |
| `attendance` | integer/null | Público | `partida.attendance` |
| `venue` | string/null | Nome do local | `estadio.name` |
| `lastUpdated` | string datetime | Revisão da fonte | `proveniencia.source_updated_at` |

## Sportmonks Football API

Entidade Fixture v3; campos selecionados.

Evidência: [documentação/arquivo original](https://docs.sportmonks.com/v3/endpoints-and-entities/entities/fixture).

| Campo nativo | Tipo | Significado | Destino sugerido |
|---|---|---|---|
| `id` | integer | ID do jogo | `partida.match_id` |
| `league_id` | integer | Liga | `partida.competition_id` |
| `season_id` | integer | Temporada | `partida.season_id` |
| `stage_id` | integer | Fase | `partida.stage` |
| `group_id` | integer/null | Grupo | `classificacao.group_id` |
| `aggregate_id` | integer/null | Eliminatória agregada | `preservar no bruto` |
| `state_id` | integer | Código de estado | `partida.status` |
| `round_id` | integer/null | Rodada | `partida.round` |
| `venue_id` | integer/null | Local | `partida.stadium_id` |
| `name` | string/null | Descrição dos participantes | `preservar no bruto` |
| `starting_at` | date/null | Início; confirmar fuso | `partida.kickoff_utc` |
| `result_info` | string/null | Resultado textual | `preservar no bruto` |
| `leg` | string | Perna da eliminatória; exige parser | `partida.leg` |
| `length` | integer/null | Duração prevista em minutos | `preservar no bruto` |

## StatsBomb Open Data

competitions.json; nomes observados na coleção.

Evidência: [documentação/arquivo original](https://raw.githubusercontent.com/hudl/open-data/master/data/competitions.json).

| Campo nativo | Tipo | Significado | Destino sugerido |
|---|---|---|---|
| `competition_id` | integer | ID da competição | `competicao.competition_id` |
| `season_id` | integer | ID da temporada | `competicao.season_id` |
| `country_name` | string | País/região; continente não vira código de país | `competicao.country_code quando aplicável` |
| `competition_name` | string | Nome da competição | `competicao.name` |
| `competition_gender` | string | Categoria de gênero | `competicao.gender_category` |
| `competition_youth` | boolean | Indicador de base | `competicao.age_category` |
| `competition_international` | boolean | Natureza internacional | `preservar no bruto` |
| `season_name` | string | Rótulo da temporada | `competicao.season_label` |
| `match_updated` | string datetime | Atualização de jogos da coleção | `proveniencia.source_updated_at` |
| `match_available_360` | string datetime/null | Disponibilidade da coleção 360; não booleano | `preservar no bruto` |

## NewsAPI

Objeto de artigo em articles[] de /v2/everything.

Evidência: [documentação/arquivo original](https://newsapi.org/docs/endpoints/everything).

| Campo nativo | Tipo | Significado | Destino sugerido |
|---|---|---|---|
| `source.id` | string/null | ID do publicador | `proveniencia.source_record_id do publicador` |
| `source.name` | string | Publicador | `noticia.publisher` |
| `author` | string/null | Autoria | `noticia.author` |
| `title` | string | Título | `noticia.title` |
| `description` | string/null | Descrição | `noticia.summary` |
| `url` | string | URL da matéria | `noticia.canonical_url` |
| `urlToImage` | string/null | Imagem relacionada | `midia.thumbnail_url` |
| `publishedAt` | string datetime | Publicação UTC | `noticia.published_at` |
| `content` | string/null | Trecho truncado; não texto integral | `preservar trecho autorizado` |

## The News API

Objeto de artigo; o envelope varia por endpoint.

Evidência: [documentação/arquivo original](https://www.thenewsapi.com/documentation).

| Campo nativo | Tipo | Significado | Destino sugerido |
|---|---|---|---|
| `uuid` | string | ID da matéria no agregador | `proveniencia.source_record_id` |
| `title` | string | Título | `noticia.title` |
| `description` | string | Metadescrição | `noticia.summary` |
| `snippet` | string | Trecho inicial | `preservar trecho autorizado` |
| `url` | string | URL da matéria | `noticia.canonical_url` |
| `image_url` | string | Imagem | `midia.thumbnail_url` |
| `language` | string | Idioma da fonte | `noticia.language` |
| `published_at` | string datetime | Publicação | `noticia.published_at` |
| `source` | string | Domínio do publicador | `noticia.publisher` |
| `categories` | array[string] | Categorias atribuídas à fonte | `preservar no bruto` |

## The Odds API

Objeto de evento com bookmakers; preços dependem de oddsFormat.

Evidência: [documentação/arquivo original](https://the-odds-api.com/liveapi/guides/v4/).

| Campo nativo | Tipo | Significado | Destino sugerido |
|---|---|---|---|
| `id` | string | Evento | `partida.match_id` |
| `sport_key` | string | Esporte/liga na API | `competicao.competition_id` |
| `commence_time` | string datetime | Início | `partida.kickoff_utc` |
| `home_team` | string | Nome do mandante; resolver ID | `partida.home_team_id` |
| `away_team` | string | Nome do visitante; resolver ID | `partida.away_team_id` |
| `bookmakers[].key` | string | Casa | `odd.bookmaker` |
| `bookmakers[].last_update` | string datetime | Atualização da casa | `proveniencia.source_updated_at` |
| `bookmakers[].markets[].key` | string | Mercado | `odd.market` |
| `bookmakers[].markets[].last_update` | string datetime | Atualização do mercado quando presente | `odd.quoted_at` |
| `bookmakers[].markets[].outcomes[].name` | string | Seleção | `odd.selection` |
| `bookmakers[].markets[].outcomes[].price` | number | Preço; solicitar formato decimal | `odd.decimal_odds` |
| `bookmakers[].markets[].outcomes[].point` | number | Linha quando aplicável | `odd.line` |

## YouTube Data API

Recurso videos; solicitar parts correspondentes.

Evidência: [documentação/arquivo original](https://developers.google.com/youtube/v3/docs/videos).

| Campo nativo | Tipo | Significado | Destino sugerido |
|---|---|---|---|
| `id` | string | ID do vídeo | `proveniencia.source_record_id` |
| `snippet.title` | string | Título | `midia.title` |
| `snippet.description` | string | Descrição | `preservar texto autorizado` |
| `snippet.publishedAt` | string datetime | Publicação | `midia.published_at` |
| `snippet.channelId` | string | Canal de origem | `preservar ID do canal` |
| `snippet.channelTitle` | string | Nome do canal | `midia.publisher` |
| `snippet.thumbnails` | string-keyed object | URLs e dimensões por variante | `midia.thumbnail_url` |
| `contentDetails.duration` | string ISO 8601 | Duração | `preservar duração normalizada` |

## Onde buscar os schemas nativos completos

- **StatsBomb:** pasta [doc](https://github.com/hudl/open-data/tree/master/doc) e arquivos JSON versionados.
- **Wyscout de pesquisa:** descritor dos autores e depósito indicados na [ficha](catalogo.md#wyscout_research).
- **Fjelstul:** codebook em [codebook/csv](https://github.com/jfjelstul/worldcup/tree/master/codebook/csv); versões CSV e PDF descritas no README.
- **API-Football:** [referência v3](https://www.api-football.com/documentation-v3) e guia oficial da ficha; a referência usa conteúdo dinâmico.
- **Football-Data.co.uk:** notas e cabeçalho de cada arquivo, acessíveis a partir da [página de dados](https://football-data.co.uk/data.php). `notes.txt` não carregou nesta pesquisa; nomes de colunas não foram certificados aqui.
- **Produtos comerciais:** solicitar schema/OpenAPI, exemplos de payload e matriz por liga-temporada ao fornecedor; versão e licença devem acompanhar a ingestão.

