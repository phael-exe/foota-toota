-- Team alias (de-para) for clubs whose name differs between sources. team_id is the
-- canonical id the silver layer uses; for the Brasileirao it is the Brasileirao Historico
-- name, so 2003-2024 history, Football-Data.co.uk (2025+) and Football-Data.org fixtures
-- all land on the same club. A name absent from this table is already canonical.
CREATE OR REPLACE TABLE `PROJECT.silver.team_alias` AS
SELECT league_id, source_id, raw_name, team_id
FROM UNNEST([
    STRUCT('brasileirao_serie_a' AS league_id, 'football_data_uk' AS source_id,
           'America MG' AS raw_name, 'America-MG' AS team_id),
    ('brasileirao_serie_a', 'football_data_uk', 'Atletico GO', 'Atletico-GO'),
    ('brasileirao_serie_a', 'football_data_uk', 'Botafogo RJ', 'Botafogo-RJ'),
    ('brasileirao_serie_a', 'football_data_uk', 'Chapecoense-SC', 'Chapecoense'),
    ('brasileirao_serie_a', 'football_data_uk', 'Flamengo RJ', 'Flamengo'),
    ('brasileirao_serie_a', 'football_data_uk', 'Sport Recife', 'Sport'),
    ('brasileirao_serie_a', 'football_data_org', 'Botafogo FR', 'Botafogo-RJ'),
    ('brasileirao_serie_a', 'football_data_org', 'CA Mineiro', 'Atletico-MG'),
    ('brasileirao_serie_a', 'football_data_org', 'CA Paranaense', 'Athletico-PR'),
    ('brasileirao_serie_a', 'football_data_org', 'CR Flamengo', 'Flamengo'),
    ('brasileirao_serie_a', 'football_data_org', 'CR Vasco da Gama', 'Vasco'),
    ('brasileirao_serie_a', 'football_data_org', 'Chapecoense AF', 'Chapecoense'),
    ('brasileirao_serie_a', 'football_data_org', 'Clube do Remo', 'Remo'),
    ('brasileirao_serie_a', 'football_data_org', 'Coritiba FBC', 'Coritiba'),
    ('brasileirao_serie_a', 'football_data_org', 'Cruzeiro EC', 'Cruzeiro'),
    ('brasileirao_serie_a', 'football_data_org', 'EC Bahia', 'Bahia'),
    ('brasileirao_serie_a', 'football_data_org', 'EC Vitória', 'Vitoria'),
    ('brasileirao_serie_a', 'football_data_org', 'Fluminense FC', 'Fluminense'),
    ('brasileirao_serie_a', 'football_data_org', 'Grêmio FBPA', 'Gremio'),
    ('brasileirao_serie_a', 'football_data_org', 'Mirassol FC', 'Mirassol'),
    ('brasileirao_serie_a', 'football_data_org', 'RB Bragantino', 'Bragantino'),
    ('brasileirao_serie_a', 'football_data_org', 'SC Corinthians Paulista', 'Corinthians'),
    ('brasileirao_serie_a', 'football_data_org', 'SC Internacional', 'Internacional'),
    ('brasileirao_serie_a', 'football_data_org', 'SE Palmeiras', 'Palmeiras'),
    ('brasileirao_serie_a', 'football_data_org', 'Santos FC', 'Santos'),
    ('brasileirao_serie_a', 'football_data_org', 'São Paulo FC', 'Sao Paulo')
]);
