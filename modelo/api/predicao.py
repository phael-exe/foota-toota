"""Vetor de entrada, probabilidades e a mensagem de predição."""

from __future__ import annotations

import uuid
from typing import Any

from .config import CLASSES, FEATURES, Liga
from .modelos import Modelo


def vetor(features: dict) -> list[float]:
    """A linha que o modelo recebe, no treino e na API: FEATURES em ordem,
    NaN onde falta dado."""
    return [
        float("nan") if features.get(nome) is None else float(features[nome])
        for nome in FEATURES
    ]


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
    features: dict,
    match_id: str,
    event_id: str | None,
    predicted_at: str,
) -> dict:
    """A mensagem do tópico `predicoes` (seção 3 do contrato)."""
    probs = probabilidades(modelo.estimador, [vetor(features)])[0]
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
    }
