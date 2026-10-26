"""API do modelo do Trabalho 2 (modelo/api.py)."""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


MODELO = Path(__file__).resolve().parent.parent / "modelo"


def _modulo(nome: str):
    spec = importlib.util.spec_from_file_location(nome, MODELO / f"{nome}.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


api = _modulo("api")

AGORA = "2026-10-16T13:15:02Z"
BSA = api.LIGAS["brasileirao_serie_a"]
EPL = api.LIGAS["epl"]
CAMPOS = {
    "prediction_id",
    "event_id",
    "match_id",
    "league_id",
    "model_name",
    "model_version",
    "prob_home",
    "prob_draw",
    "prob_away",
    "predicted_outcome",
    "predicted_at",
}


def linha(match_id="fdorg_555047", casa="Mirassol", fora="Internacional", **f):
    features = dict.fromkeys(api.FEATURES, 1.0)
    features.update(f)
    return {
        "match_id": match_id,
        "league_id": BSA.league_id,
        "season": 2026,
        "home_team_id": casa,
        "away_team_id": fora,
        "has_full_history": True,
        **features,
    }


# Mirassol (4364) x Internacional (6684) está agendado com o id fdorg_ na
# gold; o returno já foi jogado e está lá com o id da Football-Data.co.uk.
GOLD = [
    linha(),
    linha("fduk_BRA_x", "Internacional", "Mirassol", home_rest_days=9.0),
]
BRONZE = (
    json.dumps(
        {"id": 555047, "homeTeam": {"id": 4364}, "awayTeam": {"id": 6684}}
    ).encode()
    + b"\n"
)


class Relogio:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


class ModeloFalso:
    classes_ = ("away", "draw", "home")  # ordem alfabética, como no sklearn
    n_features_in_ = 15

    def __init__(self) -> None:
        self.entradas: list = []

    def predict_proba(self, x):
        self.entradas.append(x)
        return [[0.2, 0.3, 0.5]]


class FonteFalsa:
    def __init__(self) -> None:
        self.versao_atual = "3"
        self.estimador = ModeloFalso()
        self.cargas = 0
        self.falhar: Exception | None = None

    def versao(self, nome: str) -> tuple[str, str]:
        if self.falhar:
            raise self.falhar
        return self.versao_atual, f"gs://modelos/{nome}/{self.versao_atual}/"

    def carregar(self, uri: str):
        self.cargas += 1
        return self.estimador


class Loja:
    """Features com downloads falsos, contando quantas vezes leu a gold."""

    def __init__(self, linhas=GOLD, relogio=None) -> None:
        self.leituras = 0
        self.linhas = linhas

        def ler(dados: bytes, colunas: list[str]) -> list[dict]:
            self.leituras += 1
            return [dict(item) for item in self.linhas]

        def baixar(url: str) -> bytes:
            return BRONZE if url.endswith(".jsonl") else b"parquet"

        self.features = api.Features(
            BSA,
            "https://dados",
            600.0,
            baixar=baixar,
            ler=ler,
            relogio=relogio or Relogio(),
        )


@pytest.fixture
def fonte() -> FonteFalsa:
    return FonteFalsa()


@pytest.fixture
def publicadas() -> list[dict]:
    return []


@pytest.fixture
def cliente(fonte, publicadas) -> TestClient:
    app = api.criar_app(
        api.Config(verificar_token=False),
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
        publicar=publicadas.append,
        relogio=lambda: AGORA,
    )
    return TestClient(app)


def envelope(**campos) -> dict:
    evento = {
        "event_id": "fdorg_555047:TIMED:-:2026-10-16T23:00:00Z",
        "match_id": "fdorg_555047",
        "competition": "BSA",
        "season": 2026,
        "status": "TIMED",
        "home_team_id": "4364",
        "away_team_id": "6684",
        "mode": "live",
        **campos,
    }
    dados = base64.b64encode(json.dumps(evento).encode()).decode()
    return {
        "message": {
            "data": dados,
            "attributes": {"mode": evento["mode"], "competition": "BSA"},
            "messageId": "1",
        },
        "subscription": "projects/pdm-bia-505511/subscriptions/eventos-api",
    }


# --- /predict ---------------------------------------------------------------


def test_predict_devolve_e_publica_o_formato_do_contrato(cliente, publicadas):
    resp = cliente.post("/predict", json={"match_id": "fdorg_555047"})

    assert resp.status_code == 200
    corpo = resp.json()
    assert set(corpo) == CAMPOS
    assert corpo["event_id"] is None
    assert corpo["league_id"] == "brasileirao_serie_a"
    assert corpo["model_name"] == "boosted_tree_brasileirao"
    assert corpo["model_version"] == "3"
    assert (corpo["prob_home"], corpo["prob_draw"], corpo["prob_away"]) == (
        0.5,
        0.3,
        0.2,
    )
    assert corpo["predicted_outcome"] == "home"
    assert corpo["predicted_at"] == AGORA
    assert publicadas == [corpo]
    assert resp.headers["X-Publicada"] == "true"


def test_predict_partida_desconhecida_responde_404(cliente):
    resp = cliente.post("/predict", json={"match_id": "fdorg_1"})

    assert resp.status_code == 404


def test_predict_sem_publicar(cliente, publicadas):
    resp = cliente.post(
        "/predict", json={"match_id": "fdorg_555047", "publicar": False}
    )

    assert resp.status_code == 200
    assert publicadas == []


def test_predict_falha_ao_publicar_ainda_responde(fonte):
    def falhar(_: dict) -> None:
        raise RuntimeError("sem permissão no tópico")

    app = api.criar_app(
        api.Config(verificar_token=False),
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
        publicar=falhar,
    )
    resp = TestClient(app).post("/predict", json={"match_id": "fdorg_555047"})

    assert resp.status_code == 200
    assert resp.headers["X-Publicada"] == "false"


def test_predict_features_diretas_vao_na_ordem_canonica(cliente, fonte):
    features = {nome: float(i) for i, nome in enumerate(api.FEATURES)}
    del features["h2h_avg_points_last_5"]

    resp = cliente.post(
        "/predict",
        json={
            "match_id": "simulada",
            "league_id": "brasileirao_serie_a",
            "features": features,
        },
    )

    assert resp.status_code == 200
    entrada = fonte.estimador.entradas[-1][0]
    assert entrada[:10] == [float(i) for i in range(10)]
    assert entrada[10] != entrada[10]  # NaN no lugar da que faltou
    assert entrada[11:] == [float(i) for i in range(11, 15)]


@pytest.mark.parametrize(
    "pedido",
    [
        {"match_id": "x", "features": {}},
        {"match_id": "x", "league_id": "la_liga"},
        {
            "match_id": "x",
            "league_id": "brasileirao_serie_a",
            "features": {"y": 1},
        },
    ],
)
def test_predict_recusa_pedido_invalido(cliente, pedido):
    assert cliente.post("/predict", json=pedido).status_code == 422


def test_predict_liga_sem_modelo_responde_503(cliente, fonte):
    fonte.falhar = api.SemModeloError("boosted_tree_brasileirao ausente")

    resp = cliente.post("/predict", json={"match_id": "fdorg_555047"})

    assert resp.status_code == 503


# --- /pubsub ----------------------------------------------------------------


def test_pubsub_preve_partida_agendada(cliente, publicadas):
    resp = cliente.post("/pubsub", json=envelope())

    assert resp.status_code == 204
    assert len(publicadas) == 1
    assert publicadas[0]["event_id"] == (
        "fdorg_555047:TIMED:-:2026-10-16T23:00:00Z"
    )
    assert publicadas[0]["match_id"] == "fdorg_555047"


@pytest.mark.parametrize("status", ["FINISHED", "IN_PLAY", "POSTPONED"])
def test_pubsub_ignora_partida_que_nao_esta_agendada(
    cliente, publicadas, status
):
    resp = cliente.post("/pubsub", json=envelope(status=status))

    assert resp.status_code == 204
    assert publicadas == []


@pytest.mark.parametrize(
    "corpo",
    [
        b"nao e json",
        b'{"message": {}}',
        b'{"message": {"data": "%%%"}}',
        json.dumps(
            {"message": {"data": base64.b64encode(b"{}").decode()}}
        ).encode(),
    ],
)
def test_pubsub_confirma_mensagem_ilegivel(cliente, publicadas, corpo):
    resp = cliente.post("/pubsub", content=corpo)

    assert resp.status_code == 204
    assert publicadas == []


def test_pubsub_ignora_competicao_e_partida_desconhecidas(cliente, publicadas):
    outra_liga = cliente.post("/pubsub", json=envelope(competition="CL"))
    fora_da_gold = cliente.post(
        "/pubsub",
        json=envelope(match_id="fdorg_9", home_team_id="1", away_team_id="2"),
    )

    assert (outra_liga.status_code, fora_da_gold.status_code) == (204, 204)
    assert publicadas == []


def test_pubsub_descarta_evento_repetido(cliente, publicadas):
    cliente.post("/pubsub", json=envelope())
    cliente.post("/pubsub", json=envelope())

    assert len(publicadas) == 1


def test_pubsub_falha_ao_publicar_pede_reentrega(fonte):
    publicadas: list[dict] = []
    falhas = [RuntimeError("Pub/Sub fora")]

    def publicar(mensagem: dict) -> None:
        if falhas:
            raise falhas.pop()
        publicadas.append(mensagem)

    app = api.criar_app(
        api.Config(verificar_token=False),
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
        publicar=publicar,
    )
    cliente = TestClient(app)

    assert cliente.post("/pubsub", json=envelope()).status_code == 503
    assert cliente.post("/pubsub", json=envelope()).status_code == 204
    assert len(publicadas) == 1


def test_pubsub_replay_acha_a_partida_pelo_confronto(
    cliente, publicadas, fonte
):
    # O returno, já jogado: o evento traz o id fdorg_, a gold guarda fduk_
    resp = cliente.post(
        "/pubsub",
        json=envelope(
            event_id="fdorg_555011:TIMED:-:2026-09-19T21:00:00Z:replay-1",
            match_id="fdorg_555011",
            home_team_id="6684",
            away_team_id="4364",
            mode="replay",
        ),
    )

    assert resp.status_code == 204
    assert publicadas[0]["match_id"] == "fdorg_555011"
    home_rest_days = api.FEATURES.index("home_rest_days")
    assert fonte.estimador.entradas[-1][0][home_rest_days] == 9.0


def test_pubsub_sem_modelo_pede_reentrega(cliente, fonte, publicadas):
    fonte.falhar = api.SemModeloError("ainda não treinado")

    assert cliente.post("/pubsub", json=envelope()).status_code == 503
    assert publicadas == []


# --- token do push ----------------------------------------------------------


def _app_com_token(fonte, publicadas, audience="https://api/pubsub"):
    cfg = api.Config(push_audience=audience)
    app = api.criar_app(
        cfg,
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
        publicar=publicadas.append,
    )
    return TestClient(app)


def _token(monkeypatch, dados: dict) -> list:
    from google.oauth2 import id_token

    chamadas: list = []

    def verificar(token, request, audience):
        chamadas.append((token, audience))
        return dados

    monkeypatch.setattr(id_token, "verify_oauth2_token", verificar)
    return chamadas


def test_pubsub_sem_token_responde_401(fonte, publicadas):
    cliente = _app_com_token(fonte, publicadas)

    assert cliente.post("/pubsub", json=envelope()).status_code == 401
    assert publicadas == []


def test_pubsub_aceita_token_da_conta_do_push(monkeypatch, fonte, publicadas):
    chamadas = _token(
        monkeypatch,
        {
            "email": "pubsub-push@pdm-bia-505511.iam.gserviceaccount.com",
            "email_verified": True,
        },
    )
    cliente = _app_com_token(fonte, publicadas)

    resp = cliente.post(
        "/pubsub", json=envelope(), headers={"Authorization": "Bearer abc"}
    )

    assert resp.status_code == 204
    assert chamadas == [("abc", "https://api/pubsub")]
    assert len(publicadas) == 1


def test_pubsub_recusa_token_de_outra_conta(monkeypatch, fonte, publicadas):
    _token(monkeypatch, {"email": "outro@x.com", "email_verified": True})
    cliente = _app_com_token(fonte, publicadas)

    resp = cliente.post(
        "/pubsub", json=envelope(), headers={"Authorization": "Bearer abc"}
    )

    assert resp.status_code == 403
    assert publicadas == []


def test_pubsub_sem_audience_configurado_pede_reentrega(fonte, publicadas):
    cliente = _app_com_token(fonte, publicadas, audience=None)

    resp = cliente.post(
        "/pubsub", json=envelope(), headers={"Authorization": "Bearer abc"}
    )

    assert resp.status_code == 500


# --- peças ------------------------------------------------------------------


def test_prediction_id_e_estavel_por_evento():
    a = api.prediction_id("ev1", "boosted_tree_brasileirao", "3")
    b = api.prediction_id("ev1", "boosted_tree_brasileirao", "3")
    outra_versao = api.prediction_id("ev1", "boosted_tree_brasileirao", "4")
    sem_evento = api.prediction_id(None, "boosted_tree_brasileirao", "3")

    assert a == b
    assert a != outra_versao
    assert sem_evento != api.prediction_id(
        None, "boosted_tree_brasileirao", "3"
    )


def test_modelo_troca_quando_o_registry_muda_de_versao(fonte):
    relogio = Relogio()
    modelos = api.Modelos(fonte, 600.0, relogio)

    assert modelos.obter(BSA).versao == "3"
    fonte.versao_atual = "4"
    relogio.t = 599
    assert modelos.obter(BSA).versao == "3"
    relogio.t = 601
    assert modelos.obter(BSA).versao == "4"
    assert fonte.cargas == 2


def test_registry_fora_do_ar_mantem_a_versao_carregada(fonte):
    relogio = Relogio()
    modelos = api.Modelos(fonte, 600.0, relogio)
    modelos.obter(BSA)

    fonte.falhar = RuntimeError("503 do Vertex")
    relogio.t = 601

    assert modelos.obter(BSA).versao == "3"
    with pytest.raises(api.SemModeloError):
        modelos.obter(EPL)


@pytest.mark.parametrize(
    ("classes", "n_features"),
    [(("away", "home"), 15), (("away", "draw", "home"), 14)],
)
def test_validar_recusa_modelo_incompativel(classes, n_features):
    estimador = ModeloFalso()
    estimador.classes_ = classes
    estimador.n_features_in_ = n_features

    with pytest.raises(api.SemModeloError):
        api.validar(estimador)


def test_features_releem_a_gold_no_prazo_ou_quando_falta_partida():
    relogio = Relogio()
    loja = Loja(relogio=relogio)

    loja.features.buscar("fdorg_555047")
    loja.features.buscar("fdorg_555047")
    assert loja.leituras == 1

    relogio.t = 30
    assert loja.features.buscar("fdorg_novo") is None
    assert loja.leituras == 1  # releu há menos de um minuto

    loja.linhas = [*GOLD, linha("fdorg_novo")]
    relogio.t = 61
    assert loja.features.buscar("fdorg_novo") is not None
    assert loja.leituras == 2

    relogio.t = 700
    loja.features.buscar("fdorg_555047")
    assert loja.leituras == 3


def test_health_mostra_versao_e_partidas(cliente):
    cliente.post("/predict", json={"match_id": "fdorg_555047"})

    liga = cliente.get("/health").json()["ligas"]["brasileirao_serie_a"]

    assert liga["modelo"] == "boosted_tree_brasileirao"
    assert liga["versao"] == "3"
    assert liga["partidas"] == 2


# --- predição x real --------------------------------------------------------


class AvaliacaoFalsa:
    def __init__(self) -> None:
        self.tabela = "p.modelo.predicoes_vs_real"
        self.predicoes: list = []
        self.resultados: list = []
        self.falhar = False

    def predicao(self, liga, evento, mensagem) -> None:
        if self.falhar:
            raise RuntimeError("BigQuery fora")
        self.predicoes.append((liga.league_id, evento["match_id"], mensagem))

    def resultado(self, liga, evento) -> None:
        self.resultados.append((liga.league_id, evento["match_id"]))


@pytest.fixture
def avaliacao() -> AvaliacaoFalsa:
    return AvaliacaoFalsa()


@pytest.fixture
def com_tabela(fonte, publicadas, avaliacao) -> TestClient:
    app = api.criar_app(
        api.Config(verificar_token=False),
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
        publicar=publicadas.append,
        avaliacao=avaliacao,
        relogio=lambda: AGORA,
    )
    return TestClient(app)


def test_agendada_grava_a_predicao_antes_de_publicar(
    com_tabela, avaliacao, publicadas
):
    assert com_tabela.post("/pubsub", json=envelope()).status_code == 204

    assert len(avaliacao.predicoes) == 1
    liga, match_id, mensagem = avaliacao.predicoes[0]
    assert (liga, match_id) == ("brasileirao_serie_a", "fdorg_555047")
    assert publicadas == [mensagem]


def test_encerrada_grava_o_resultado_na_mesma_partida(
    com_tabela, avaliacao, publicadas
):
    resp = com_tabela.post(
        "/pubsub",
        json=envelope(
            event_id="fdorg_555047:FINISHED:2-1:2026-10-16T23:00:00Z",
            status="FINISHED",
            score_home=2,
            score_away=1,
        ),
    )

    assert resp.status_code == 204
    assert avaliacao.resultados == [("brasileirao_serie_a", "fdorg_555047")]
    assert publicadas == []


def test_falha_na_tabela_pede_reentrega_sem_publicar(
    com_tabela, avaliacao, publicadas
):
    avaliacao.falhar = True

    assert com_tabela.post("/pubsub", json=envelope()).status_code == 503
    assert publicadas == []


def test_health_mostra_a_tabela(com_tabela):
    corpo = com_tabela.get("/health").json()

    assert corpo["predicoes_vs_real"] == "p.modelo.predicoes_vs_real"


@pytest.mark.parametrize(
    ("casa", "fora", "esperado"),
    [(2, 1, "home"), (1, 1, "draw"), (0, 3, "away"), (None, 1, None)],
)
def test_resultado_real(casa, fora, esperado):
    evento = {"score_home": casa, "score_away": fora}

    assert api.resultado_real(evento) == esperado


class ClienteBQ:
    def __init__(self) -> None:
        self.consultas: list = []

    def query(self, sql, job_config=None):
        assert job_config is not None
        parametros = {
            p.name: (p.type_, p.value) for p in job_config.query_parameters
        }
        self.consultas.append((sql, parametros))

        class Job:
            def result(self, timeout=None):
                return []

        return Job()


def _evento(**campos) -> dict:
    return json.loads(base64.b64decode(envelope(**campos)["message"]["data"]))


def test_merge_da_predicao_so_mexe_nas_colunas_da_predicao():
    cliente = ClienteBQ()
    tabela = api.Avaliacao("p.modelo.predicoes_vs_real", cliente)
    mensagem = {
        "prediction_id": "x",
        "event_id": "e",
        "model_name": "boosted_tree_brasileirao",
        "model_version": "1",
        "prob_home": 0.5,
        "prob_draw": 0.3,
        "prob_away": 0.2,
        "predicted_outcome": "home",
        "predicted_at": AGORA,
    }

    tabela.predicao(BSA, _evento(kickoff_utc="2026-10-16T23:00:00Z"), mensagem)

    sql, parametros = cliente.consultas[0]
    assert "MERGE `p.modelo.predicoes_vs_real` t" in sql
    assert "ON t.match_id = s.match_id" in sql
    assert "predicted_outcome = s.predicted_outcome" in sql
    assert "score_home = s.score_home" not in sql
    assert "s.predicted_outcome = t.real_outcome" in sql
    assert parametros["match_id"] == ("STRING", "fdorg_555047")
    assert parametros["season"] == ("INT64", 2026)
    tipo, kickoff = parametros["kickoff_utc"]
    assert tipo == "TIMESTAMP"
    assert kickoff.isoformat() == "2026-10-16T23:00:00+00:00"


def test_merge_do_resultado_calcula_o_real_e_o_acerto():
    cliente = ClienteBQ()
    tabela = api.Avaliacao("p.modelo.predicoes_vs_real", cliente)

    tabela.resultado(
        BSA,
        _evento(
            status="FINISHED",
            score_home=0,
            score_away=1,
            source_updated_at="2026-10-17T01:00:00Z",
        ),
    )

    sql, parametros = cliente.consultas[0]
    assert "t.predicted_outcome = s.real_outcome" in sql
    assert "prob_home" not in sql
    assert parametros["real_outcome"] == ("STRING", "away")
    assert parametros["score_away"] == ("INT64", 1)
    assert parametros["result_at"][1].isoformat() == "2026-10-17T01:00:00+00:00"


def test_inicio_carrega_features_e_modelo_antes_do_primeiro_pedido(fonte):
    loja = Loja()
    app = api.criar_app(
        api.Config(verificar_token=False),
        features={BSA.league_id: loja.features},
        modelos=api.Modelos(fonte, 600.0),
        publicar=lambda mensagem: None,
        aquecer=True,
    )

    with TestClient(app) as cliente:
        assert (loja.leituras, fonte.cargas) == (1, 1)
        liga = cliente.get("/health").json()["ligas"]["brasileirao_serie_a"]

    assert (liga["versao"], liga["partidas"]) == ("3", 2)


def test_inicio_sobe_mesmo_sem_modelo(fonte):
    fonte.falhar = api.SemModeloError("ainda não treinado")
    app = api.criar_app(
        api.Config(verificar_token=False),
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
        publicar=lambda mensagem: None,
        aquecer=True,
    )

    with TestClient(app) as cliente:
        assert cliente.get("/health").status_code == 200
