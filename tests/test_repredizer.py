"""Repredição diária dos próximos jogos (scripts/repredizer.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "repredizer", RAIZ / "scripts" / "repredizer.py"
)
assert _spec is not None and _spec.loader is not None
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)


def jogo(i: int, liga: str = "brasileirao_serie_a") -> dict:
    return {
        "match_id": f"fdorg_{i}",
        "league_id": liga,
        "kickoff_utc": "2026-11-18 00:00:00",
    }


def test_lotes_respeitam_o_maximo_da_api():
    lotes = rp.lotes([jogo(i) for i in range(230)], tamanho=100)
    assert [len(lote) for lote in lotes] == [100, 100, 30]
    assert lotes[0][0] == {
        "match_id": "fdorg_0",
        "league_id": "brasileirao_serie_a",
    }


def test_so_predicoes_que_deram_certo_viram_linha():
    jogos = {"fdorg_1": jogo(1), "fdorg_2": jogo(2)}
    resultados = [
        {
            "match_id": "fdorg_1",
            "status": 200,
            "motivo": None,
            "predicao": {
                "prediction_id": "p1",
                "match_id": "fdorg_1",
                "league_id": "brasileirao_serie_a",
                "model_name": "boosted_tree_brasileirao",
                "model_version": "3",
                "prob_home": 0.5,
                "prob_draw": 0.3,
                "prob_away": 0.2,
                "predicted_outcome": "home",
                "predicted_at": "2026-11-15T09:00:00Z",
                "features_ate": "2026-11-09T00:30:00Z",
            },
        },
        {
            "match_id": "fdorg_2",
            "status": 404,
            "motivo": "fora_da_gold",
            "predicao": None,
        },
    ]

    linhas, falhas = rp.linhas(resultados, jogos)

    assert falhas == {"fora_da_gold": 1}
    assert linhas == [
        {
            "prediction_id": "p1",
            "match_id": "fdorg_1",
            "league_id": "brasileirao_serie_a",
            "model_name": "boosted_tree_brasileirao",
            "model_version": "3",
            "prob_home": 0.5,
            "prob_draw": 0.3,
            "prob_away": 0.2,
            "predicted_outcome": "home",
            "predicted_at": "2026-11-15T09:00:00Z",
            "kickoff_utc": "2026-11-18 00:00:00",
            "features_ate": "2026-11-09T00:30:00Z",
            "mode": "lote",
        }
    ]


def test_consulta_pega_so_jogos_agendados_das_ligas_com_modelo():
    sql = rp.consulta("p", dias=7)
    assert "`p.gold.match_features`" in sql
    assert "status = 'scheduled'" in sql
    assert "'brasileirao_serie_a'" in sql and "'epl'" in sql
    assert "INTERVAL 7 DAY" in sql


def test_a_tabela_tem_as_colunas_que_o_script_grava():
    import re

    texto = (
        RAIZ / "sql" / "10_stream" / "09a_create_table_predicoes_lote.sql"
    ).read_text()
    colunas = set(
        re.findall(r"^\s+(\w+)\s+(?:STRING|FLOAT64|TIMESTAMP)", texto, re.M)
    )
    assert colunas == set(rp.COLUNAS)
