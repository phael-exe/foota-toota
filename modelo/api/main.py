"""Ponto de entrada do serviço: `uvicorn api.main:app`."""

from __future__ import annotations

import logging
import os

from .rotas import criar_app


logging.basicConfig(
    level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
)
app = criar_app(aquecer=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
