"""Rotas HTTP da API do modelo."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from .config import LIGAS, Config, Liga, agora
from .features import Features
from .modelos import Modelos, SemCampeaoError, SemModeloError, fonte_padrao
from .predicao import predicao


log = logging.getLogger("modelo")


class FalhaError(Exception):
    """Um pedido que não vira predição. `motivo` é o que o Dataflow lê para
    decidir se re-tenta (503) ou registra e segue (404, 409, 422)."""

    def __init__(self, status: int, motivo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.motivo = motivo
        self.mensagem = mensagem

    def http(self) -> HTTPException:
        detalhe = {"motivo": self.motivo, "mensagem": self.mensagem}
        return HTTPException(self.status, detalhe)


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
                    "motivo": "sem_campeao"
                    if modelos_.sem_campeao(loja.liga)
                    else None,
                    "partidas": len(loja),
                    "features_lidas_em": loja.lido_em,
                }
                for liga_id, loja in lojas.items()
            },
        }

    def localizar(pedido: Pedido) -> tuple[Liga, dict]:
        if pedido.league_id is not None and pedido.league_id not in lojas:
            raise FalhaError(
                422,
                "pedido_invalido",
                f"league_id desconhecido; use um de {sorted(lojas)}",
            )
        if pedido.features is not None:
            if pedido.league_id is None:
                raise FalhaError(
                    422, "pedido_invalido", "features diretas pedem league_id"
                )
            return lojas[pedido.league_id].liga, pedido.features
        candidatas = (
            [lojas[pedido.league_id]] if pedido.league_id else lojas.values()
        )
        for loja in candidatas:
            try:
                linha = loja.buscar(pedido.match_id)
            except Exception as erro:
                log.exception("%s: gold", loja.liga.league_id)
                raise FalhaError(
                    503, "indisponivel", "gold indisponível"
                ) from erro
            if linha is not None:
                return loja.liga, linha
        raise FalhaError(
            404, "fora_da_gold", f"{pedido.match_id} não está na gold"
        )

    def modelo_da(liga: Liga) -> Any:
        try:
            return modelos_.obter(liga)
        except SemCampeaoError as erro:
            raise FalhaError(409, "sem_campeao", str(erro)) from erro
        except SemModeloError as erro:
            raise FalhaError(503, "indisponivel", str(erro)) from erro

    def prever(pedido: Pedido) -> dict:
        """A predição do pedido, ou FalhaError."""
        liga, linha = localizar(pedido)
        modelo = modelo_da(liga)
        if pedido.features is not None:
            sobra = sorted(set(pedido.features) - set(modelo.features))
            if sobra:
                raise FalhaError(
                    422, "pedido_invalido", f"features desconhecidas: {sobra}"
                )
        else:
            colunas = lojas[liga.league_id].colunas
            faltam = sorted(set(modelo.features) - colunas)
            if faltam:
                raise FalhaError(
                    503, "features_ausentes", f"a gold não tem {faltam}"
                )
        return predicao(liga, modelo, linha, pedido.match_id, None, relogio())

    @app.post("/predict")
    def predict(pedido: Pedido) -> dict:
        try:
            return prever(pedido)
        except FalhaError as falha:
            raise falha.http() from falha

    return app
