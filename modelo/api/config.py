"""Constantes, ligas e configuração da API do modelo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]

PIPELINE = "pdm-bia-505511"

DADOS = "https://storage.googleapis.com/foota-toota-505511"

CLASSES = ("home", "draw", "away")

# Ordem canônica: a do SELECT de sql/06_model e do array que o modelo
# recebe. Mudar a ordem exige retreinar.
FEATURES = (
    "home_avg_points_last_5",
    "home_avg_goals_for_last_5",
    "home_avg_goals_against_last_5",
    "home_avg_points_season",
    "home_rest_days",
    "away_avg_points_last_5",
    "away_avg_goals_for_last_5",
    "away_avg_goals_against_last_5",
    "away_avg_points_season",
    "away_rest_days",
    "h2h_avg_points_last_5",
    "diff_avg_points_last_5",
    "diff_avg_goals_for_last_5",
    "diff_avg_goals_against_last_5",
    "diff_avg_points_season",
)


@dataclass(frozen=True)
class Liga:
    league_id: str  # id da silver
    competicao: str  # código do Football-Data.org nos eventos
    modelo: str  # display_name no Model Registry
    gold: str  # arquivo no bucket público
    bronze_fdorg: str | None = None  # partidas do Football-Data.org


LIGAS = {
    liga.league_id: liga
    for liga in (
        Liga(
            "brasileirao_serie_a",
            "BSA",
            "boosted_tree_brasileirao",
            "gold/match_features_brasileirao.parquet",
            "bronze/football_data_org/competition=BSA/matches.jsonl",
        ),
        # Só no batch, com ids da Big Balls: entra pelo /predict
        Liga(
            "epl", "PL", "boosted_tree_epl", "gold/match_features_epl.parquet"
        ),
    )
}


@dataclass(frozen=True)
class Config:
    projeto: str | None = None
    regiao: str = "us-central1"
    alias: str = "campeao"
    dados_url: str = DADOS
    modelos_dir: str | None = None
    recarregar_s: float = 600.0

    @classmethod
    def do_ambiente(cls) -> Config:
        env = ambiente()
        return cls(
            projeto=env.get("MODELO_PROJECT_ID") or env.get("GCP_PROJECT_ID"),
            regiao=env.get("MODELO_REGIAO", cls.regiao),
            alias=env.get("ALIAS_MODELO", cls.alias),
            dados_url=env.get("DADOS_URL", cls.dados_url),
            modelos_dir=env.get("MODELOS_DIR") or None,
            recarregar_s=float(env.get("RECARREGAR_SEGUNDOS", "600")),
        )


def ambiente() -> dict[str, str]:
    """O ambiente completado pelo .env da raiz, sem alterar os.environ."""
    valores: dict[str, str] = {}
    env = RAIZ / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                valores[chave.strip()] = valor.strip().strip("'\"")
    return {**valores, **os.environ}


def agora() -> str:
    """Instante atual em UTC, ISO 8601 com sufixo Z."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
