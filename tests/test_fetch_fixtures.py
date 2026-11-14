"""Odds dos próximos jogos do Football-Data.co.uk (scripts/fetch_bronze.py)."""

from __future__ import annotations

import csv
import importlib.util
import io
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "fetch_bronze", RAIZ / "scripts" / "fetch_bronze.py"
)
assert _spec is not None and _spec.loader is not None
fb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fb)


FIXTURES = (
    "﻿Div,Date,Time,HomeTeam,AwayTeam,Referee,B365H,B365D,B365A,PSH,PSD,PSA,"
    "AvgH,AvgD,AvgA,B365CH\n"
    "E0,21/11/2026,15:00,Arsenal,Chelsea,M Oliver,1.8,3.9,4.5,1.82,3.95,4.6,"
    "1.79,3.85,4.4,1.7\n"
    "E3,21/11/2026,15:00,Barrow,Bromley,,2.1,3.3,3.4,,,,2.05,3.3,3.5,\n"
)
NOVAS = (
    "﻿Country,League,Date,Time,Home,Away,PSH,PSD,PSA,MaxH,MaxD,MaxA,"
    "AvgH,AvgD,AvgA,B365H,B365D,B365A\n"
    "Brazil,Serie A,14/11/2026,21:30,Mirassol,Atletico-MG,1.94,3.6,4.1,2,3.7,"
    "4.3,1.9,3.5,4,1.91,3.5,4\n"
    "Mexico,Liga MX,14/11/2026,02:00,Toluca,America,2.1,3.4,3.3,,,,2,3.3,3.4,"
    "2,3.4,3.4\n"
)


def linhas(texto: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(texto)))


def test_junta_as_ligas_que_temos_num_formato_so():
    saida = fb.normalize_fixtures(FIXTURES, NOVAS)

    assert saida.splitlines()[0] == ",".join(fb.FIXTURES_COLUMNS)
    jogos = linhas(saida)
    assert [(j["Div"], j["HomeTeam"], j["AwayTeam"]) for j in jogos] == [
        ("E0", "Arsenal", "Chelsea"),
        ("BRA", "Mirassol", "Atletico-MG"),
    ]
    epl, bra = jogos
    assert (epl["PSH"], epl["AvgH"], epl["B365H"]) == ("1.82", "1.79", "1.8")
    assert (bra["PSH"], bra["AvgA"], bra["Date"]) == ("1.94", "4", "14/11/2026")


def test_arquivo_ausente_nao_derruba_o_outro():
    so_brasil = linhas(fb.normalize_fixtures(None, NOVAS))
    assert [j["Div"] for j in so_brasil] == ["BRA"]
    assert fb.normalize_fixtures(None, None).strip() == ",".join(
        fb.FIXTURES_COLUMNS
    )


def test_premier_league_tem_historico_de_odds_desde_2014():
    temporadas = {nome for _, nome in fb.EPL_HISTORICO}
    assert "2014-2015" in temporadas and "2021-2022" in temporadas
