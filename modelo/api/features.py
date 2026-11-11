"""Features da gold pública de cada liga."""

from __future__ import annotations

import io
import json
import logging
import threading
import time
from collections.abc import Callable

from .config import COLUNAS, Liga, agora


log = logging.getLogger("modelo")


def baixar_publico(url: str) -> bytes:
    import httpx

    resp = httpx.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def ler_parquet(dados: bytes, colunas: list[str]) -> list[dict]:
    import pyarrow.parquet as pq

    return pq.read_table(io.BytesIO(dados), columns=colunas).to_pylist()


class Features:
    """Features da gold de uma liga, por match_id e por confronto.

    Relê o arquivo quando passa de `recarregar_s`. Uma partida que não está
    lá força uma releitura, no máximo uma por minuto, para um jogo recém-
    exportado aparecer sem esperar o prazo.
    """

    def __init__(
        self,
        liga: Liga,
        dados_url: str,
        recarregar_s: float,
        baixar: Callable[[str], bytes] = baixar_publico,
        ler: Callable[[bytes, list[str]], list[dict]] = ler_parquet,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self.liga = liga
        self._url = dados_url.rstrip("/")
        self._recarregar_s = recarregar_s
        self._baixar = baixar
        self._ler = ler
        self._relogio = relogio
        self._trava = threading.Lock()
        self._por_id: dict[str, dict] = {}
        self._por_confronto: dict[tuple, dict] = {}
        self._clubes: dict[str, str] = {}
        self._lido_em: float | None = None
        self.lido_em: str | None = None

    def __len__(self) -> int:
        return len(self._por_id)

    def buscar(self, match_id: str, evento: dict | None = None) -> dict | None:
        with self._trava:
            self._atualizar(self._recarregar_s)
            linha = self._achar(match_id, evento)
            if linha is None:
                self._atualizar(60.0)
                linha = self._achar(match_id, evento)
            return linha

    def _achar(self, match_id: str, evento: dict | None) -> dict | None:
        linha = self._por_id.get(match_id)
        if linha is not None or not evento:
            return linha
        chave = (
            evento.get("season"),
            self._clubes.get(str(evento.get("home_team_id"))),
            self._clubes.get(str(evento.get("away_team_id"))),
        )
        return self._por_confronto.get(chave)

    def _atualizar(self, idade_maxima: float) -> None:
        if (
            self._lido_em is not None
            and self._relogio() - self._lido_em < idade_maxima
        ):
            return
        url = f"{self._url}/{self.liga.gold}"
        linhas = self._ler(self._baixar(url), COLUNAS)
        self._por_id = {linha["match_id"]: linha for linha in linhas}
        self._por_confronto = {
            (linha["season"], linha["home_team_id"], linha["away_team_id"]): (
                linha
            )
            for linha in linhas
        }
        if self.liga.bronze_fdorg:
            try:
                self._clubes = self._clubes_fdorg()
            except Exception:
                log.exception("%s: de-para de clubes", self.liga.league_id)
        self._lido_em = self._relogio()
        self.lido_em = agora()
        log.info(
            "%s: %d partidas, %d clubes no de-para",
            self.liga.league_id,
            len(self._por_id),
            len(self._clubes),
        )

    def _clubes_fdorg(self) -> dict[str, str]:
        """Id do clube no Football-Data.org -> id da silver, pelas partidas
        que a gold guarda com o id `fdorg_` (as agendadas)."""
        url = f"{self._url}/{self.liga.bronze_fdorg}"
        clubes: dict[str, str] = {}
        for texto in self._baixar(url).decode("utf-8").splitlines():
            if not texto.strip():
                continue
            partida = json.loads(texto)
            linha = self._por_id.get(f"fdorg_{partida.get('id')}")
            if linha is None:
                continue
            for lado, coluna in (
                ("homeTeam", "home_team_id"),
                ("awayTeam", "away_team_id"),
            ):
                clube = (partida.get(lado) or {}).get("id")
                if clube is not None:
                    clubes[str(clube)] = linha[coluna]
        return clubes
