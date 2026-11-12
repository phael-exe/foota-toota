"""Disparo do replay: valida os parâmetros e monta a chamada do Cloud Run Job.

O replay da demo só usa temporadas que o modelo em produção não viu: o split
do treino é por temporada, e o TEST nunca entra na escolha nem no ajuste.
"""

from __future__ import annotations

import re

from foota.config import BUCKET_BRONZE, PROJETO, TABELA_SPLIT


# O formato de producer._rodadas: "31", "28-30", "5,7", "28-30,32"
_RODADAS = re.compile(r"\d+(-\d+)?(,\d+(-\d+)?)*")


def validar_rodadas(texto: str) -> str:
    rodadas = texto.strip()
    if not _RODADAS.fullmatch(rodadas):
        raise ValueError(
            f"rodadas inválidas: {texto!r} (use 31, 28-30 ou 5,7)"
        )
    return rodadas


def _tabela_split(competicao: str) -> str:
    if competicao not in TABELA_SPLIT:
        conhecidas = ", ".join(TABELA_SPLIT)
        raise ValueError(
            f"competição {competicao} sem modelo (use {conhecidas})"
        )
    return TABELA_SPLIT[competicao]


def consulta_primeira_test(competicao: str) -> str:
    tabela = _tabela_split(competicao)
    return (
        "SELECT MIN(season) AS primeira\n"
        f"FROM `{PROJETO}.{tabela}`\n"
        "WHERE split_set = 'TEST'"
    )


def checar_fora_da_amostra(
    competicao: str, temporada: int, primeira_test: int | None
) -> None:
    if primeira_test is None:
        raise ValueError(f"{competicao} sem TEST no split do treino")
    if temporada < primeira_test:
        raise ValueError(
            f"temporada {temporada} do {competicao} está em TRAIN/EVAL do "
            f"modelo; o TEST começa em {primeira_test}"
        )


def argumentos_replay(
    competicao: str, temporada: int, rodadas: str, intervalo: float
) -> list[str]:
    _tabela_split(competicao)
    arquivo = (
        f"gs://{BUCKET_BRONZE}/bronze/football_data_org/"
        f"competition={competicao}/matches.jsonl"
    )
    return [
        "python",
        "producer.py",
        "replay",
        "--arquivo",
        arquivo,
        "--temporada",
        str(temporada),
        "--rodadas",
        validar_rodadas(rodadas),
        "--intervalo",
        str(intervalo),
    ]


def overrides(args: list[str]) -> dict:
    """Os argumentos no formato de RunJobRequest.Overrides do Cloud Run."""
    return {"container_overrides": [{"args": args}]}
