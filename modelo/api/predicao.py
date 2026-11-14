"""Vetor de entrada, probabilidades e a mensagem de predição."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from .config import CLASSES, FEATURES, Liga
from .modelos import Modelo


def vetor(linha: dict, nomes: Sequence[str] = FEATURES) -> list[float]:
    """A entrada do modelo, no treino e na API: as features da versão na
    ordem dela, NaN onde falta dado."""
    return [
        float("nan") if linha.get(nome) is None else float(linha[nome])
        for nome in nomes
    ]


def instante(valor: Any) -> str | None:
    """datetime (o parquet traz TIMESTAMP assim) em ISO 8601 UTC com Z."""
    if isinstance(valor, datetime):
        return valor.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return valor


def probabilidades(estimador: Any, x: list[list[float]]) -> list[dict]:
    """Probabilidade de cada resultado, por linha de x."""
    classes = [str(c) for c in estimador.classes_]
    return [
        {c: float(p) for c, p in zip(classes, linha, strict=True)}
        for linha in estimador.predict_proba(x)
    ]


def prediction_id(event_id: str | None, nome: str, versao: str) -> str:
    """Igual para o mesmo evento e a mesma versão: a reentrega do Pub/Sub
    gera o mesmo id, e as linhas repetidas em stream.predicoes ficam fáceis
    de descartar. Sem evento (o /predict), um UUID novo."""
    if event_id is None:
        return str(uuid.uuid4())
    chave = f"foota-toota/{event_id}/{nome}/{versao}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chave))


def predicao(
    liga: Liga,
    modelo: Modelo,
    linha: dict,
    match_id: str,
    event_id: str | None,
    predicted_at: str,
) -> dict:
    """A predição no formato da seção 3 do contrato. `features_ate` é o
    instante do último dado usado nas features, quando a gold o traz."""
    x = [vetor(linha, modelo.features)]
    probs = probabilidades(modelo.estimador, x)[0]
    return {
        "prediction_id": prediction_id(event_id, liga.modelo, modelo.versao),
        "event_id": event_id,
        "match_id": match_id,
        "league_id": liga.league_id,
        "model_name": liga.modelo,
        "model_version": modelo.versao,
        "prob_home": round(probs["home"], 4),
        "prob_draw": round(probs["draw"], 4),
        "prob_away": round(probs["away"], 4),
        "predicted_outcome": max(CLASSES, key=probs.__getitem__),
        "predicted_at": predicted_at,
        "features_ate": instante(linha.get("features_ate")),
    }
