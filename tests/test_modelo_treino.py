"""Treino e registro dos modelos (modelo/treinar.py)."""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from pathlib import Path

import pytest


MODELO = Path(__file__).resolve().parent.parent / "modelo"


def _modulo(nome: str):
    spec = importlib.util.spec_from_file_location(nome, MODELO / f"{nome}.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


api = _modulo("api")
treinar = _modulo("treinar")

BSA = api.LIGAS["brasileirao_serie_a"]
PAI = "projects/p/locations/us-central1/models/9"
BUSCA = {"grade": {"max_depth": (2,), "learning_rate": (0.1,)}, "maximo": 30}


def linha(split="TRAIN", resultado="home", historico=True, forca=0.0):
    features = dict.fromkeys(api.FEATURES, 1.0)
    features["diff_avg_points_season"] = forca
    return {
        "split_set": split,
        "label_outcome": resultado,
        "has_full_history": historico,
        **features,
    }


def temporada(split: str, n: int, semente: int) -> list[dict]:
    """Partidas em que a diferença de pontos decide quase sempre."""
    sorteio = random.Random(semente)
    linhas = []
    for _ in range(n):
        forca = sorteio.uniform(-2, 2)
        if abs(forca) < 0.3:
            resultado = "draw"
        else:
            resultado = "home" if forca > 0 else "away"
        if sorteio.random() < 0.1:
            resultado = sorteio.choice(api.CLASSES)
        linhas.append(linha(split, resultado, forca=forca))
    return linhas


GOLD = (
    temporada("TRAIN", 600, 1)
    + temporada("EVAL", 150, 2)
    + temporada("TEST", 150, 3)
)


class Uniforme:
    """Um campeão que não sabe nada: 1/3 para cada resultado."""

    classes_ = ("away", "draw", "home")

    def predict_proba(self, x):
        return [[1 / 3] * 3 for _ in x]


# --- treino -----------------------------------------------------------------


def test_separar_deixa_so_historico_completo_e_resultado():
    conjuntos = treinar.separar(
        [
            linha("TRAIN", "home"),
            linha("TRAIN", "away", historico=False),
            linha("TEST", None),
            linha("PREDICT", None),
            linha("EVAL", "draw", forca=0.5),
        ]
    )

    assert [len(c.y) for c in conjuntos.values()] == [1, 1, 0]
    indice = api.FEATURES.index("diff_avg_points_season")
    assert conjuntos["EVAL"].x[0][indice] == 0.5


def test_metricas():
    m = treinar.metricas(
        ["home", "away"],
        [
            {"home": 0.5, "draw": 0.3, "away": 0.2},
            {"home": 0.2, "draw": 0.3, "away": 0.5},
        ],
    )

    assert m["n"] == 2
    assert m["acuracia"] == 1.0
    assert m["log_loss"] == pytest.approx(-math.log(0.5))
    assert m["brier"] == pytest.approx(0.38)


@pytest.mark.parametrize(
    ("modelo", "campeao", "reprovacoes"),
    [
        ({"acuracia": 0.50, "log_loss": 1.00}, None, 0),
        ({"acuracia": 0.40, "log_loss": 1.00}, None, 1),
        ({"acuracia": 0.50, "log_loss": 1.10}, None, 1),
        ({"acuracia": 0.50, "log_loss": 1.00}, {"log_loss": 0.99}, 1),
        ({"acuracia": 0.50, "log_loss": 1.00}, {"log_loss": 1.01}, 0),
    ],
)
def test_decidir(modelo, campeao, reprovacoes):
    motivos = treinar.decidir(modelo, 0.45, {"log_loss": 1.05}, campeao)

    assert len(motivos) == reprovacoes


def test_treinar_liga_aprova_modelo_que_bate_baselines_e_campeao():
    estimador, relatorio = treinar.treinar_liga(
        BSA, GOLD, lambda liga: ("1", Uniforme()), **BUSCA
    )

    assert api.validar(estimador) is estimador
    assert relatorio["partidas"] == {"TRAIN": 600, "EVAL": 150, "TEST": 150}
    assert 1 <= relatorio["hiperparametros"]["max_iter"] <= 30
    teste = relatorio["teste"]
    assert teste["campeao"]["versao"] == "1"
    assert teste["modelo"]["log_loss"] < teste["campeao"]["log_loss"]
    assert relatorio["aprovado"], relatorio["motivos"]


def test_treinar_liga_reprova_quem_nao_bate_o_campeao():
    campeao, _ = treinar.treinar_liga(BSA, GOLD, lambda liga: None, **BUSCA)

    _, relatorio = treinar.treinar_liga(
        BSA, GOLD, lambda liga: ("4", campeao), **BUSCA
    )

    # O mesmo modelo empata com o campeão: empate não promove
    assert not relatorio["aprovado"]
    assert "campeão" in relatorio["motivos"][0]


# --- Registry ---------------------------------------------------------------


class Resposta:
    def __init__(self, dados=None, status: int = 200) -> None:
        self.dados = dados or {}
        self.status_code = status

    def json(self):
        return self.dados

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class Sessao:
    """Responde pela primeira rota cujo trecho aparece na URL."""

    def __init__(self, rotas: dict) -> None:
        self.rotas = rotas
        self.chamadas: list = []

    def _responder(self, url: str) -> Resposta:
        for trecho, resposta in self.rotas.items():
            if trecho in url:
                return resposta() if callable(resposta) else resposta
        return Resposta(status=404)

    def get(self, url, params=None):
        self.chamadas.append(("GET", url, params))
        return self._responder(url)

    def post(self, url, json=None):
        self.chamadas.append(("POST", url, json))
        return self._responder(url)


def registry(rotas: dict):
    sessao = Sessao(rotas)
    return api.Registry("p", "us-central1", "campeao", sessao=sessao), sessao


def _aliases(sessao: Sessao) -> list:
    return [
        (url.rsplit("@", 1)[1], corpo["versionAliases"])
        for metodo, url, corpo in sessao.chamadas
        if metodo == "POST" and url.endswith(":mergeVersionAliases")
    ]


def test_promover_tira_o_alias_do_anterior_e_poe_no_novo():
    reg, sessao = registry(
        {"@campeao": Resposta({"versionId": "1"}), "mergeVersion": Resposta()}
    )

    anterior = treinar.promover(reg, PAI, "2")

    assert anterior == "1"
    assert _aliases(sessao) == [
        ("1:mergeVersionAliases", ["-campeao"]),
        ("2:mergeVersionAliases", ["campeao"]),
    ]


def test_promover_primeira_versao_so_poe_o_alias():
    reg, sessao = registry({"mergeVersion": Resposta()})

    assert treinar.promover(reg, PAI, "1") is None
    assert _aliases(sessao) == [("1:mergeVersionAliases", ["campeao"])]


def test_registrar_cria_versao_do_modelo_existente(monkeypatch):
    monkeypatch.setattr(treinar.time, "sleep", lambda s: None)
    operacoes = iter(
        [
            Resposta({"name": "op/1", "done": False}),
            Resposta(
                {
                    "name": "op/1",
                    "done": True,
                    "response": {"model": PAI, "modelVersionId": "2"},
                }
            ),
        ]
    )
    reg, sessao = registry(
        {
            "models:upload": Resposta({"name": "op/1"}),
            "op/1": lambda: next(operacoes),
            "/models": Resposta({"models": [{"name": PAI}]}),
        }
    )

    pai, versao = treinar.registrar(
        reg, "boosted_tree_brasileirao", "gs://b/x/", "desc", {"liga": "bsa"}
    )

    assert (pai, versao) == (PAI, "2")
    corpo = next(c for m, u, c in sessao.chamadas if u.endswith(":upload"))
    assert corpo["parentModel"] == PAI
    assert corpo["model"]["artifactUri"] == "gs://b/x/"
    assert corpo["model"]["containerSpec"]["imageUri"] == treinar.SERVING


def test_registrar_falha_se_a_operacao_falhar():
    reg, _ = registry(
        {
            "models:upload": Resposta(
                {"name": "op/1", "done": True, "error": {"message": "x"}}
            ),
            "/models": Resposta({"models": []}),
        }
    )

    with pytest.raises(RuntimeError, match="upload"):
        treinar.registrar(reg, "boosted_tree_epl", "gs://b/x/", "d", {})


def test_modelo_atual_so_tolera_falha_no_modo_sem_registrar():
    class Quebrado:
        def versao(self, nome):
            raise RuntimeError("sem credenciais")

    assert treinar.modelo_atual(Quebrado(), tolerar=True)(BSA) is None
    with pytest.raises(RuntimeError):
        treinar.modelo_atual(Quebrado())(BSA)


# --- Experiments ------------------------------------------------------------


def _relatorio(campeao: bool = True) -> dict:
    _, relatorio = treinar.treinar_liga(
        BSA,
        GOLD,
        (lambda liga: ("1", Uniforme())) if campeao else (lambda liga: None),
        **BUSCA,
    )
    relatorio["execucao"] = "20261019t051751z"
    return relatorio


def test_nome_run_segue_o_formato_do_vertex():
    assert treinar.nome_run(_relatorio()) == (
        "brasileirao-serie-a-20261019t051751z"
    )


def test_run_do_experimento_aprovado_leva_versao_e_campeao():
    parametros, metricas = treinar.run_do_experimento(
        _relatorio(), "2", "gs://b/x/"
    )

    assert parametros["decisao"] == "aprovado"
    assert parametros["versao_registry"] == "2"
    assert parametros["campeao_comparado"] == "1"
    assert {"test_log_loss", "mandante_acuracia", "campeao_log_loss"} <= set(
        metricas
    )
    valores = [*parametros.values(), *metricas.values()]
    assert all(isinstance(v, str | int | float) for v in valores)


def test_run_do_experimento_reprovado_nao_tem_versao():
    relatorio = _relatorio(campeao=False)
    relatorio["aprovado"] = False
    relatorio["motivos"] = ["log loss não passa o campeão"]

    parametros, metricas = treinar.run_do_experimento(relatorio, None, None)

    assert parametros["decisao"] == "reprovado"
    assert parametros["versao_registry"] == "-"
    assert parametros["motivos"] == "log loss não passa o campeão"
    assert "campeao_log_loss" not in metricas


def test_experimento_grava_o_run_sem_tensorboard(monkeypatch):
    chamadas: list = []

    class SDK:
        def init(self, **kwargs):
            chamadas.append(("init", kwargs))

        def start_run(self, run, resume=False):
            chamadas.append(("start_run", run, resume))
            if not resume:
                raise RuntimeError("run já existe")

        def log_params(self, parametros):
            chamadas.append(("log_params", parametros["decisao"]))

        def log_metrics(self, metricas):
            chamadas.append(("log_metrics", sorted(metricas)[0]))

        def end_run(self):
            chamadas.append(("end_run",))

    monkeypatch.setitem(sys.modules, "google.cloud.aiplatform", SDK())

    run = treinar.experimento("p", "us-central1", _relatorio(), "2", "gs://b/")

    assert run == "brasileirao-serie-a-20261019t051751z"
    init = chamadas[0][1]
    assert init["experiment"] == treinar.EXPERIMENTO
    assert init["experiment_tensorboard"] is False
    assert [c[0] for c in chamadas] == [
        "init",
        "start_run",
        "start_run",
        "log_params",
        "log_metrics",
        "end_run",
    ]
    assert chamadas[2] == ("start_run", run, True)
