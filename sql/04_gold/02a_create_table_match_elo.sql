-- Elo rating of both clubs before each match: the long-run strength that the last-5 and
-- season windows miss. One row per match of silver.matches, scheduled ones included (they get
-- the current rating), so the model API finds it for the games it predicts.
-- Per league, in kickoff order, using ONLY finished matches that kicked off earlier:
--   expected = 1 / (1 + 10^((away - home - h) / 400)),  delta = k * mult * (result - expected)
--   result 1 / 0.5 / 0; mult = ln(|goal diff| + 1) + 1 when `margem`, else 1.
-- At each new season every rating moves `regressao` of the way to the league mean. A club that
-- arrives after the first season (promoted) starts at the league mean + `novo`.
-- k, h, regressao, novo and margem were chosen by EVAL log loss (never TEST) for the two leagues
-- with a model; the others use the Brasileirao set.
CREATE TEMP FUNCTION elo(
    jogos ARRAY<STRUCT<match_id STRING, season FLOAT64, home STRING, away STRING,
                       gh FLOAT64, ga FLOAT64, finished BOOL>>,
    k FLOAT64, h FLOAT64, regressao FLOAT64, novo FLOAT64, margem BOOL
)
RETURNS ARRAY<STRUCT<match_id STRING, elo_home FLOAT64, elo_away FLOAT64>>
LANGUAGE js AS r"""
  var r = {};
  var temporada = null;
  var houveTemporada = false;
  var saida = [];
  function media() {
    var soma = 0, n = 0;
    for (var t in r) { soma += r[t]; n++; }
    return n ? soma / n : 1500;
  }
  for (var i = 0; i < jogos.length; i++) {
    var j = jogos[i];
    if (temporada === null || j.season !== temporada) {
      if (temporada !== null) {
        var m0 = media();
        for (var t in r) { r[t] = m0 + (1 - regressao) * (r[t] - m0); }
      }
      houveTemporada = temporada !== null;
      temporada = j.season;
    }
    var inicial = houveTemporada ? media() + novo : 1500;
    if (!(j.home in r)) { r[j.home] = inicial; }
    if (!(j.away in r)) { r[j.away] = inicial; }
    var rh = r[j.home], ra = r[j.away];
    saida.push({match_id: j.match_id, elo_home: rh, elo_away: ra});
    if (!j.finished || j.gh === null || j.ga === null) { continue; }
    var esperado = 1 / (1 + Math.pow(10, (ra - rh - h) / 400));
    var real = j.gh > j.ga ? 1 : (j.gh === j.ga ? 0.5 : 0);
    var mult = (margem && j.gh !== j.ga) ? Math.log(Math.abs(j.gh - j.ga) + 1) + 1 : 1;
    var delta = k * mult * (real - esperado);
    r[j.home] = rh + delta;
    r[j.away] = ra - delta;
  }
  return saida;
""";

CREATE OR REPLACE TABLE `PROJECT.gold.match_elo` AS
WITH parametros AS (
    SELECT * FROM UNNEST([
        STRUCT('brasileirao_serie_a' AS league_id, 20.0 AS k, 60.0 AS h, 0.25 AS regressao,
               0.0 AS novo, FALSE AS margem),
        STRUCT('epl', 20.0, 90.0, 0.0, -100.0, TRUE)
    ])
),
ligas AS (
    SELECT
        m.league_id,
        ARRAY_AGG(
            STRUCT(
                m.match_id,
                CAST(m.season AS FLOAT64) AS season,
                m.home_team_id AS home,
                m.away_team_id AS away,
                CAST(m.score_home AS FLOAT64) AS gh,
                CAST(m.score_away AS FLOAT64) AS ga,
                m.status = 'finished' AS finished
            )
            ORDER BY m.kickoff_utc, m.match_id
        ) AS jogos
    FROM `PROJECT.silver.matches` m
    GROUP BY m.league_id
)
SELECT
    l.league_id,
    e.match_id,
    e.elo_home,
    e.elo_away,
    e.elo_home - e.elo_away AS elo_diff,
    1 / (1 + POW(10, (e.elo_away - e.elo_home - COALESCE(p.h, 60.0)) / 400)) AS elo_p_home
FROM ligas l
LEFT JOIN parametros p USING (league_id)
CROSS JOIN UNNEST(elo(
    l.jogos,
    COALESCE(p.k, 20.0), COALESCE(p.h, 60.0), COALESCE(p.regressao, 0.25),
    COALESCE(p.novo, 0.0), COALESCE(p.margem, FALSE)
)) AS e;
