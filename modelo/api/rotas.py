"""Rotas HTTP da API do modelo."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from .config import FEATURES, LIGAS, Config, Liga, agora
from .features import Features
from .modelos import Modelos, SemModeloError, fonte_padrao
from .predicao import predicao


log = logging.getLogger("modelo")


class Pedido(BaseModel):
    match_id: str
    league_id: str | None = None
    # Features diretas, para simular uma partida: as que faltam viram NaN
    features: dict[str, float | None] | None = None


def criar_app(
    cfg: Config | None = None,
    *,
    features: dict[str, Features] | None = None,
    modelos: Modelos | None = None,
    relogio: Callable[[], str] = agora,
    aquecer: bool = False,
) -> FastAPI:
    cfg = cfg or Config.do_ambiente()
    if features is None:
        features = {
            liga.league_id: Features(liga, cfg.dados_url, cfg.recarregar_s)
            for liga in LIGAS.values()
        }
    lojas = features
    modelos_ = modelos or Modelos(fonte_padrao(cfg), cfg.recarregar_s)

    def aquecer_tudo() -> None:
        """Lê features e modelos antes de aceitar pedidos; o que falhar é
        lido de novo no primeiro uso, sem impedir o serviço de subir."""
        for loja in lojas.values():
            try:
                loja.buscar("")
                modelos_.obter(loja.liga)
            except Exception as erro:
                log.warning("%s: aquecimento: %s", loja.liga.league_id, erro)

    @asynccontextmanager
    async def ciclo(_: FastAPI) -> AsyncIterator[None]:
        # Na inicialização, não numa thread: o Cloud Run só dá CPU durante
        # pedidos, e uma thread em segundo plano ficava parada até o
        # primeiro /predict. O uvicorn só abre a porta depois disto, então
        # o Cloud Run segura o primeiro pedido até tudo estar carregado.
        if aquecer:
            await run_in_threadpool(aquecer_tudo)
        yield

    app = FastAPI(title="Foota Toota: modelo", lifespan=ciclo)

    @app.get("/health")
    def saude() -> dict:
        return {
            "ligas": {
                liga_id: {
                    "modelo": loja.liga.modelo,
                    "versao": modelos_.versao(loja.liga),
                    "partidas": len(loja),
                    "features_lidas_em": loja.lido_em,
                }
                for liga_id, loja in lojas.items()
            },
        }

    def localizar(pedido: Pedido) -> tuple[Liga, dict]:
        if pedido.league_id is not None and pedido.league_id not in lojas:
            raise HTTPException(
                422, f"league_id desconhecido; use um de {sorted(lojas)}"
            )
        if pedido.features is not None:
            if pedido.league_id is None:
                raise HTTPException(422, "features diretas pedem league_id")
            sobra = sorted(set(pedido.features) - set(FEATURES))
            if sobra:
                raise HTTPException(422, f"features desconhecidas: {sobra}")
            return lojas[pedido.league_id].liga, pedido.features
        candidatas = (
            [lojas[pedido.league_id]] if pedido.league_id else lojas.values()
        )
        for loja in candidatas:
            try:
                linha = loja.buscar(pedido.match_id)
            except Exception as erro:
                log.exception("%s: gold", loja.liga.league_id)
                raise HTTPException(503, "gold indisponível") from erro
            if linha is not None:
                return loja.liga, linha
        raise HTTPException(404, f"{pedido.match_id} não está na gold")

    @app.post("/predict")
    def predict(pedido: Pedido) -> dict:
        liga, linha = localizar(pedido)
        try:
            modelo = modelos_.obter(liga)
        except SemModeloError as erro:
            raise HTTPException(503, str(erro)) from erro
        return predicao(liga, modelo, linha, pedido.match_id, None, relogio())

    return app
