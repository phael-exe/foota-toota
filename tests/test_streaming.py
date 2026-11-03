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
