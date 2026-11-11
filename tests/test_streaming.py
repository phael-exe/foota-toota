"""Coletor e limpeza do pipeline de streaming (streaming/)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


STREAMING = Path(__file__).resolve().parent.parent / "streaming"


def _modulo(nome: str):
    spec = importlib.util.spec_from_file_location(
        nome, STREAMING / f"{nome}.py"
    )
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


producer = _modulo("producer")
pipeline = _modulo("pipeline")

AGORA = "2026-10-16T12:00:00.000Z"


def partida(
    id_=555023, status="FINISHED", casa=2, fora=0, rodada=29, data=None
):
    return {
        "id": id_,
        "utcDate": data or "2026-10-08T00:30:00Z",
        "status": status,
        "matchday": rodada,
        "lastUpdated": "2026-10-15T00:20:32Z",
        "competition": {"code": "BSA"},
        "season": {"startDate": "2026-01-28"},
        "homeTeam": {"id": 1771, "name": "Cruzeiro EC"},
        "awayTeam": {"id": 1776, "name": "São Paulo FC"},
        "score": {
            "winner": "HOME_TEAM",
            "fullTime": {"home": casa, "away": fora},
        },
    }


def mensagem(**campos) -> bytes:
    ev = producer.evento(partida(), "live", AGORA)
    ev.update(campos)
    return json.dumps(ev).encode()


# --- coletor ----------------------------------------------------------------


def test_evento_converte_a_partida():
    ev = producer.evento(partida(), "live", AGORA)

    assert ev["match_id"] == "fdorg_555023"
    assert ev["competition"] == "BSA"
    assert ev["season"] == 2026
    assert ev["home_team_id"] == "1771"
    assert (ev["score_home"], ev["score_away"]) == (2, 0)
    assert ev["event_id"] == "fdorg_555023:FINISHED:2-0:2026-10-08T00:30:00Z"


def test_event_id_depende_so_da_versao_da_partida():
    antes = producer.evento(partida(), "live", AGORA)
    depois = producer.evento(partida(), "live", "2026-10-17T00:00:00.000Z")
    agendada = producer.evento(
        partida(status="TIMED", casa=None, fora=None), "live", AGORA
    )

    assert antes["event_id"] == depois["event_id"]
    assert agendada["event_id"] == "fdorg_555023:TIMED:-:2026-10-08T00:30:00Z"


def test_mudancas_publica_so_o_que_mudou():
    publicado = producer.evento(partida(), "live", AGORA)
    estado = {publicado["match_id"]: publicado["event_id"]}
    partidas = [
        partida(),
        partida(id_=555024, status="TIMED", casa=None, fora=None),
    ]

    novos = producer.mudancas(partidas, estado, AGORA)

    assert [e["match_id"] for e in novos] == ["fdorg_555024"]


def test_mudancas_nao_desfaz_partida_encerrada():
    encerrada = producer.evento(partida(), "live", AGORA)
    estado = {encerrada["match_id"]: encerrada["event_id"]}
    cache_antigo = partida(status="TIMED", casa=None, fora=None)
    placar_corrigido = partida(casa=3, fora=0)

    assert producer.mudancas([cache_antigo], estado, AGORA) == []
    assert [
        e["score_home"]
        for e in producer.mudancas([placar_corrigido], estado, AGORA)
    ] == [3]


def test_linha_do_tempo_agenda_a_rodada_antes_dos_resultados():
    partidas = [
        partida(id_=2, rodada=30, data="2026-10-11T19:00:00Z"),
        partida(id_=1, rodada=30, data="2026-10-10T21:00:00Z"),
        partida(id_=3, rodada=29),
        partida(id_=4, status="TIMED", casa=None, fora=None, rodada=31),
    ]

    linha = producer.linha_do_tempo(partidas, rodadas={29, 30})

    assert [(p["id"], p["status"]) for p in linha] == [
        (3, "TIMED"),
        (3, "FINISHED"),
        (1, "TIMED"),
        (2, "TIMED"),
        (1, "FINISHED"),
        (2, "FINISHED"),
    ]
    assert linha[0]["score"]["fullTime"] == {"home": None, "away": None}
    assert partidas[2]["score"]["fullTime"] == {"home": 2, "away": 0}


def test_rodadas_aceita_intervalo_e_lista():
    assert producer._rodadas("28-30") == {28, 29, 30}
    assert producer._rodadas("5,7") == {5, 7}


# --- limpeza do pipeline ----------------------------------------------------


def test_evento_do_coletor_passa_na_limpeza():
    destino, linha = pipeline.limpar(mensagem(), AGORA)

    assert destino == pipeline.LIMPA
    assert linha["league_id"] == "brasileirao_serie_a"
    assert linha["status"] == "finished"
    assert linha["outcome"] == "home"
    assert linha["round"] == "29"
    assert linha["kickoff_utc"] == "2026-10-08T00:30:00+00:00"
    assert linha["processed_at"] == AGORA


@pytest.mark.parametrize(
    ("casa", "fora", "resultado"), [(0, 0, "draw"), (1, 3, "away")]
)
def test_resultado_vem_do_placar(casa, fora, resultado):
    _, linha = pipeline.limpar(
        mensagem(score_home=casa, score_away=fora), AGORA
    )

    assert linha["outcome"] == resultado


def test_agendada_perde_o_placar():
    destino, linha = pipeline.limpar(
        mensagem(status="TIMED", score_home=0, score_away=0), AGORA
    )

    assert destino == pipeline.LIMPA
    assert linha["status"] == "scheduled"
    assert (linha["score_home"], linha["score_away"], linha["outcome"]) == (
        None,
        None,
        None,
    )


@pytest.mark.parametrize(
    ("mensagem_", "motivo"),
    [
        (b"{nao e json", "Expecting"),
        (b"[1, 2]", "não é um objeto"),
        (mensagem(match_id=None), "campos ausentes: match_id"),
        (mensagem(status="QUALQUER"), "status desconhecido"),
        (mensagem(competition="XYZ"), "competição desconhecida"),
        (mensagem(away_team_id="1771"), "mesmo time"),
        (mensagem(score_home=None), "encerrada sem placar"),
        (mensagem(score_home=-1), "placar negativo"),
        (mensagem(score_home="dois"), "não é inteiro"),
        (mensagem(kickoff_utc="ontem"), "não é uma data"),
    ],
)
def test_evento_invalido_vai_para_rejeitadas(mensagem_, motivo):
    destino, linha = pipeline.limpar(mensagem_, AGORA)

    assert destino == pipeline.REJEITADA
    assert motivo in linha["reason"]
    assert linha["payload"] == mensagem_.decode()
    assert linha["processed_at"] == AGORA


# --- inferência -------------------------------------------------------------


def linha_agendada(**campos):
    _, linha = pipeline.limpar(
        mensagem(status="TIMED", score_home=None, score_away=None), AGORA
    )
    return {**linha, **campos}


def predicao_api(event_id="e1", **campos):
    return {
        "prediction_id": "p-" + event_id,
        "event_id": event_id,
        "match_id": "fdorg_555023",
        "league_id": "brasileirao_serie_a",
        "model_name": "boosted_tree_brasileirao",
        "model_version": "1",
        "prob_home": 0.5,
        "prob_draw": 0.3,
        "prob_away": 0.2,
        "predicted_outcome": "home",
        "predicted_at": "2026-10-16T12:00:01Z",
        "features_ate": "2026-10-01T00:00:00Z",
        **campos,
    }


def item(status, ev, predicao=None, motivo=None):
    return {
        "match_id": "fdorg_555023",
        "event_id": ev,
        "status": status,
        "predicao": predicao,
        "motivo": motivo,
    }


class Api:
    """Responde em ordem as respostas dadas e guarda os pedidos."""

    def __init__(self, *respostas):
        self.respostas, self.chamadas = list(respostas), []

    def __call__(self, pedidos):
        self.chamadas.append(pedidos)
        return self.respostas.pop(0)


def sem_espera(_segundos):
    pass


def test_so_partida_agendada_pede_predicao():
    assert pipeline.precisa_predicao(linha_agendada())
    assert not pipeline.precisa_predicao(linha_agendada(status="finished"))
    assert not pipeline.precisa_predicao(linha_agendada(status="in_play"))


def test_pedido_leva_o_confronto_e_o_codigo_da_competicao():
    p = pipeline.pedido(linha_agendada(event_id="e1"))
    assert p == {
        "match_id": "fdorg_555023",
        "event_id": "e1",
        "competition": "BSA",
        "season": 2026,
        "home_team_id": "1771",
        "away_team_id": "1776",
    }


def test_lote_previsto_volta_enriquecido_e_sem_falha():
    linhas = [linha_agendada(event_id="e1"), linha_agendada(event_id="e2")]
    api = Api(
        (
            200,
            {
                "resultados": [
                    item(200, "e1", predicao_api("e1")),
                    item(200, "e2", predicao_api("e2")),
                ]
            },
        )
    )
    saida, falhas = pipeline.prever_lote(linhas, api, AGORA, dormir=sem_espera)
    assert falhas == []
    assert [linha["prediction_id"] for linha in saida] == ["p-e1", "p-e2"]
    assert saida[0]["predicted_outcome"] == "home"
    assert saida[0]["features_ate"] == "2026-10-01T00:00:00+00:00"
    assert saida[0]["status"] == "scheduled"


def test_4xx_de_um_item_vira_falha_sem_nova_tentativa():
    linhas = [linha_agendada(event_id="e1"), linha_agendada(event_id="e2")]
    api = Api(
        (
            200,
            {
                "resultados": [
                    item(200, "e1", predicao_api("e1")),
                    item(409, "e2", motivo="sem_campeao"),
                ]
            },
        )
    )
    saida, falhas = pipeline.prever_lote(linhas, api, AGORA, dormir=sem_espera)
    assert len(api.chamadas) == 1
    assert saida[1]["prediction_id"] is None
    assert set(pipeline.COLUNAS_PREDICAO) <= set(saida[1])
    assert falhas == [
        {
            "event_id": "e2",
            "match_id": "fdorg_555023",
            "league_id": "brasileirao_serie_a",
            "status": 409,
            "motivo": "sem_campeao",
            "tentativas": 1,
            "processed_at": AGORA,
        }
    ]


def test_item_503_tenta_de_novo_so_ele_com_backoff():
    linhas = [linha_agendada(event_id="e1"), linha_agendada(event_id="e2")]
    esperas = []
    api = Api(
        (
            200,
            {
                "resultados": [
                    item(200, "e1", predicao_api("e1")),
                    item(503, "e2", motivo="indisponivel"),
                ]
            },
        ),
        (200, {"resultados": [item(200, "e2", predicao_api("e2"))]}),
    )
    saida, falhas = pipeline.prever_lote(
        linhas, api, AGORA, dormir=esperas.append
    )
    assert [len(c) for c in api.chamadas] == [2, 1]
    assert api.chamadas[1][0]["event_id"] == "e2"
    assert esperas == [1.0]
    assert falhas == []
    assert saida[1]["prediction_id"] == "p-e2"


def test_timeout_esgota_as_tentativas_e_vira_falha():
    esperas = []
    api = Api(*[(0, {"motivo": "timeout"})] * 4)
    saida, falhas = pipeline.prever_lote(
        [linha_agendada(event_id="e1")], api, AGORA, dormir=esperas.append
    )
    assert esperas == [1.0, 2.0, 4.0]
    assert saida[0]["prediction_id"] is None
    assert falhas[0]["status"] is None
    assert falhas[0]["motivo"] == "timeout"
    assert falhas[0]["tentativas"] == 4


@pytest.mark.parametrize(
    ("status", "motivo"),
    [(401, "nao_autorizado"), (403, "nao_autorizado"), (422, "http_422")],
)
def test_lote_4xx_falha_tudo_sem_nova_tentativa(status, motivo):
    api = Api((status, None))
    saida, falhas = pipeline.prever_lote(
        [linha_agendada(event_id="e1")], api, AGORA, dormir=sem_espera
    )
    assert len(api.chamadas) == 1
    assert len(saida) == 1
    assert falhas[0]["motivo"] == motivo
    assert falhas[0]["status"] == status


@pytest.mark.parametrize("corpo", [None, {}, {"resultados": []}])
def test_resposta_malformada_vira_falha_e_a_linha_segue(corpo):
    api = Api((200, corpo))
    saida, falhas = pipeline.prever_lote(
        [linha_agendada(event_id="e1")], api, AGORA, dormir=sem_espera
    )
    assert len(api.chamadas) == 1
    assert saida[0]["event_id"] == "e1"
    assert saida[0]["prediction_id"] is None
    assert falhas[0]["motivo"] == "resposta_invalida"


class SessaoHttp:
    def __init__(self, erro=None):
        self.erro, self.posts = erro, []

    def post(self, url, json, timeout):
        self.posts.append((url, json, timeout))
        if self.erro:
            raise self.erro

        class Resposta:
            status_code = 200

            def json(self):
                return {"resultados": []}

        return Resposta()


def test_enviar_http_manda_o_lote_e_traduz_timeout():
    import requests

    s = SessaoHttp()
    enviar = pipeline.enviar_http(s, "https://api")
    assert enviar([{"match_id": "m"}]) == (200, {"resultados": []})
    assert s.posts == [
        ("https://api/predict/lote", {"pedidos": [{"match_id": "m"}]}, (5, 60))
    ]
    lento = pipeline.enviar_http(SessaoHttp(requests.Timeout()), "https://api")
    assert lento([]) == (0, {"motivo": "timeout"})
    fora = pipeline.enviar_http(
        SessaoHttp(requests.ConnectionError()), "https://api"
    )
    assert fora([]) == (0, {"motivo": "conexao"})


def test_enviar_http_traduz_outros_erros_de_rede_e_de_token():
    import requests
    from google.auth.exceptions import RefreshError

    partido = SessaoHttp(requests.exceptions.ChunkedEncodingError())
    assert pipeline.enviar_http(partido, "https://api")([]) == (
        0,
        {"motivo": "conexao"},
    )
    sem_token = SessaoHttp(RefreshError("metadata"))
    assert pipeline.enviar_http(sem_token, "https://api")([]) == (
        0,
        {"motivo": "token"},
    )


@pytest.mark.parametrize(
    "predicao",
    [
        None,
        "texto",
        predicao_api("e1", prediction_id=None),
        predicao_api("e1", predicted_at="ontem"),
    ],
)
def test_item_200_malformado_vira_resposta_invalida(predicao):
    api = Api((200, {"resultados": [item(200, "e1", predicao)]}))
    saida, falhas = pipeline.prever_lote(
        [linha_agendada(event_id="e1")], api, AGORA, dormir=sem_espera
    )
    assert saida[0]["prediction_id"] is None
    assert falhas[0]["motivo"] == "resposta_invalida"


def test_erro_inesperado_do_cliente_nao_segura_as_partidas():
    def quebra(_pedidos):
        raise ValueError("url inválida")

    saida, falhas = pipeline.prever_lote(
        [linha_agendada(event_id="e1")], quebra, AGORA, dormir=sem_espera
    )
    assert saida[0]["event_id"] == "e1"
    assert saida[0]["prediction_id"] is None
    assert falhas[0]["motivo"] == "erro_cliente"
