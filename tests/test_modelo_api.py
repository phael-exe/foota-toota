"""API do modelo (modelo/api/)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


MODELO = Path(__file__).resolve().parent.parent / "modelo"


sys.path.insert(0, str(MODELO))
import api  # noqa: E402


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
    "features_ate",
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
        self.features = api.FEATURES
        self.cargas = 0
        self.falhar: Exception | None = None

    def versao(self, nome: str) -> tuple[str, str]:
        if self.falhar:
            raise self.falhar
        return self.versao_atual, f"gs://modelos/{nome}/{self.versao_atual}/"

    def carregar(self, uri: str):
        self.cargas += 1
        return self.estimador, self.features


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
def cliente(fonte) -> TestClient:
    app = api.criar_app(
        api.Config(),
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
        relogio=lambda: AGORA,
    )
    return TestClient(app)


# --- /predict ---------------------------------------------------------------


def test_predict_devolve_o_formato_do_contrato(cliente):
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


def test_predict_partida_desconhecida_responde_404(cliente):
    resp = cliente.post("/predict", json={"match_id": "fdorg_1"})

    assert resp.status_code == 404


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


def test_inicio_carrega_features_e_modelo_antes_do_primeiro_pedido(fonte):
    loja = Loja()
    app = api.criar_app(
        api.Config(),
        features={BSA.league_id: loja.features},
        modelos=api.Modelos(fonte, 600.0),
        aquecer=True,
    )

    with TestClient(app) as cliente:
        assert (loja.leituras, fonte.cargas) == (1, 1)
        liga = cliente.get("/health").json()["ligas"]["brasileirao_serie_a"]

    assert (liga["versao"], liga["partidas"]) == ("3", 2)


def test_inicio_sobe_mesmo_sem_modelo(fonte):
    fonte.falhar = api.SemModeloError("ainda não treinado")
    app = api.criar_app(
        api.Config(),
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
        aquecer=True,
    )

    with TestClient(app) as cliente:
        assert cliente.get("/health").status_code == 200


def test_rota_pubsub_nao_existe_mais(cliente):
    assert cliente.post("/pubsub", json={}).status_code == 404


def test_pacote_nao_cria_app_ao_importar():
    assert not hasattr(api, "app")


def test_predicao_usa_as_features_da_versao(cliente, fonte):
    fonte.features = ("home_rest_days", "away_rest_days")
    fonte.estimador.n_features_in_ = 2

    resp = cliente.post("/predict", json={"match_id": "fduk_BRA_x"})

    assert resp.status_code == 200
    assert fonte.estimador.entradas[-1] == [[9.0, 1.0]]


def test_predicao_traz_features_ate(fonte):
    ate = datetime(2026, 10, 12, 21, 0, tzinfo=UTC)
    app = api.criar_app(
        api.Config(),
        features={BSA.league_id: Loja([linha(features_ate=ate)]).features},
        modelos=api.Modelos(fonte, 600.0),
        relogio=lambda: AGORA,
    )

    resp = TestClient(app).post("/predict", json={"match_id": "fdorg_555047"})

    assert resp.json()["features_ate"] == "2026-10-12T21:00:00Z"


def test_predicao_sem_features_ate_na_gold_devolve_none(cliente):
    resp = cliente.post("/predict", json={"match_id": "fdorg_555047"})

    assert resp.json()["features_ate"] is None


def test_liga_sem_campeao_responde_409(cliente, fonte):
    fonte.falhar = api.SemCampeaoError("sem alias campeao")

    resp = cliente.post("/predict", json={"match_id": "fdorg_555047"})

    assert resp.status_code == 409
    assert resp.json()["detail"]["motivo"] == "sem_campeao"


def test_alias_removido_para_de_servir(fonte):
    relogio = Relogio()
    modelos = api.Modelos(fonte, 600.0, relogio=relogio)
    modelos.obter(BSA)
    fonte.falhar = api.SemCampeaoError("alias removido")
    relogio.t = 601

    with pytest.raises(api.SemCampeaoError):
        modelos.obter(BSA)
    assert modelos.versao(BSA) is None


def test_registry_fora_sem_modelo_carregado_responde_503(cliente, fonte):
    fonte.falhar = RuntimeError("timeout")

    resp = cliente.post("/predict", json={"match_id": "fdorg_555047"})

    assert resp.status_code == 503
    assert resp.json()["detail"]["motivo"] == "indisponivel"


def test_partida_fora_da_gold_responde_404_com_motivo(cliente):
    resp = cliente.post("/predict", json={"match_id": "nao_existe"})

    assert resp.status_code == 404
    assert resp.json()["detail"]["motivo"] == "fora_da_gold"


def test_health_mostra_liga_sem_campeao(cliente, fonte):
    fonte.falhar = api.SemCampeaoError("sem alias campeao")
    cliente.post("/predict", json={"match_id": "fdorg_555047"})

    liga = cliente.get("/health").json()["ligas"]["brasileirao_serie_a"]

    assert liga["versao"] is None
    assert liga["motivo"] == "sem_campeao"


# --- contexto do evento e lote ----------------------------------------------


def test_predict_acha_a_partida_pelo_confronto(cliente, fonte):
    # O returno, já jogado: o evento traz o id fdorg_, a gold guarda fduk_
    resp = cliente.post(
        "/predict",
        json={
            "match_id": "fdorg_555011",
            "competition": "BSA",
            "season": 2026,
            "home_team_id": "6684",
            "away_team_id": "4364",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["match_id"] == "fdorg_555011"
    home_rest_days = api.FEATURES.index("home_rest_days")
    assert fonte.estimador.entradas[-1][0][home_rest_days] == 9.0


def test_prediction_id_estavel_com_event_id(cliente):
    pedido = {"match_id": "fdorg_555047", "event_id": "ev-1"}

    a = cliente.post("/predict", json=pedido).json()
    b = cliente.post("/predict", json=pedido).json()

    assert a["prediction_id"] == b["prediction_id"]
    assert a["event_id"] == "ev-1"


def test_competicao_sem_liga_responde_409(cliente):
    resp = cliente.post(
        "/predict", json={"match_id": "x", "competition": "ELC"}
    )

    assert resp.status_code == 409
    assert resp.json()["detail"]["motivo"] == "sem_campeao"


def test_lote_com_resultados_mistos(cliente):
    resp = cliente.post(
        "/predict/lote",
        json={
            "pedidos": [
                {"match_id": "fdorg_555047", "event_id": "ev-1"},
                {"match_id": "nao_existe"},
                {"match_id": "x", "competition": "ELC"},
            ]
        },
    )

    assert resp.status_code == 200
    resultados = resp.json()["resultados"]
    assert [r["status"] for r in resultados] == [200, 404, 409]
    assert [r["motivo"] for r in resultados] == [
        None,
        "fora_da_gold",
        "sem_campeao",
    ]
    assert resultados[0]["predicao"]["event_id"] == "ev-1"
    assert resultados[0]["event_id"] == "ev-1"
    assert resultados[1]["predicao"] is None
    assert [r["match_id"] for r in resultados] == [
        "fdorg_555047",
        "nao_existe",
        "x",
    ]


def test_lote_acima_de_100_responde_422(cliente):
    pedidos = [{"match_id": "fdorg_555047"}] * 101

    assert (
        cliente.post("/predict/lote", json={"pedidos": pedidos}).status_code
        == 422
    )


def test_lote_le_a_gold_uma_vez_por_liga(fonte):
    loja = Loja()
    app = api.criar_app(
        api.Config(),
        features={BSA.league_id: loja.features},
        modelos=api.Modelos(fonte, 600.0),
    )
    pedidos = [{"match_id": "fdorg_555047"}] * 50

    resp = TestClient(app).post("/predict/lote", json={"pedidos": pedidos})

    assert {r["status"] for r in resp.json()["resultados"]} == {200}
    assert loja.leituras == 1


# --- revisão final ----------------------------------------------------------


def test_lote_isola_erro_inesperado_de_um_pedido(fonte):
    class Quebra(ModeloFalso):
        def predict_proba(self, x):
            if x[0][0] == 9.0:  # só a partida fduk_BRA_x
                raise ValueError("entrada inválida")
            return super().predict_proba(x)

    fonte.estimador = Quebra()
    fonte.features = ("home_rest_days",)
    fonte.estimador.n_features_in_ = 1
    app = api.criar_app(
        api.Config(),
        features={BSA.league_id: Loja().features},
        modelos=api.Modelos(fonte, 600.0),
    )

    resp = TestClient(app).post(
        "/predict/lote",
        json={
            "pedidos": [
                {"match_id": "fduk_BRA_x"},
                {"match_id": "fdorg_555047"},
            ]
        },
    )

    assert resp.status_code == 200
    resultados = resp.json()["resultados"]
    assert [r["status"] for r in resultados] == [500, 200]
    assert resultados[0]["motivo"] == "erro_interno"


def test_features_ausentes_nao_e_passageiro(cliente, fonte):
    fonte.features = ("home_rest_days", "coluna_que_nao_existe")
    fonte.estimador.n_features_in_ = 2

    resp = cliente.post("/predict", json={"match_id": "fdorg_555047"})

    assert resp.status_code == 409
    assert resp.json()["detail"]["motivo"] == "features_ausentes"


def test_sem_campeao_fica_em_cache_ate_a_proxima_conferencia(fonte):
    class Contadora(FonteFalsa):
        def __init__(self) -> None:
            super().__init__()
            self.consultas = 0

        def versao(self, nome):
            self.consultas += 1
            return super().versao(nome)

    contadora = Contadora()
    contadora.falhar = api.SemCampeaoError("sem alias")
    relogio = Relogio()
    modelos = api.Modelos(contadora, 600.0, relogio=relogio)

    for _ in range(5):
        with pytest.raises(api.SemCampeaoError):
            modelos.obter(BSA)

    assert contadora.consultas == 1
    relogio.t = 601
    contadora.falhar = None
    assert modelos.obter(BSA).versao == "3"


def test_registry_lento_numa_liga_nao_trava_as_outras(fonte):
    import threading

    epl = api.LIGAS["epl"]
    liberar = threading.Event()
    entrou = threading.Event()

    class Lenta(FonteFalsa):
        travar = False

        def versao(self, nome):
            if self.travar and nome == BSA.modelo:
                entrou.set()
                liberar.wait(5)
            return super().versao(nome)

    lenta = Lenta()
    relogio = Relogio()
    modelos = api.Modelos(lenta, 600.0, relogio=relogio)
    modelos.obter(BSA)
    relogio.t = 500
    modelos.obter(epl)
    relogio.t = 601  # BSA vencida, EPL ainda válida
    lenta.travar = True
    fio = threading.Thread(target=modelos.obter, args=(BSA,))
    fio.start()
    entrou.wait(5)

    resultado: list = []
    outro = threading.Thread(
        target=lambda: resultado.append(modelos.obter(epl))
    )
    outro.start()
    outro.join(1)
    liberar.set()
    fio.join(5)

    assert resultado, "EPL ficou esperando o Registry da BSA"
