"""Modelos de cada liga: Vertex AI Model Registry ou pasta local."""

from __future__ import annotations

import io
import json
import logging
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import CLASSES, FEATURES, Config, Liga


log = logging.getLogger("modelo")

# Uma chamada ao Registry que passa disso conta como falha passageira
REGISTRY_TIMEOUT_S = 30.0


class SemModeloError(Exception):
    """A liga não tem modelo utilizável no Registry (ou na pasta local)."""


class SemCampeaoError(SemModeloError):
    """Nenhuma versão aprovada: o modelo não existe ou nenhuma versão tem o
    alias `campeao`. Não é falha passageira: re-tentar não adianta."""


@dataclass(frozen=True)
class Modelo:
    estimador: Any
    versao: str
    features: tuple[str, ...] = FEATURES


class Fonte(Protocol):
    def versao(self, nome: str) -> tuple[str, str]:
        """(version_id, uri do artefato) da versão que vale agora."""
        ...

    def carregar(self, uri: str) -> tuple[Any, tuple[str, ...]]:
        """(estimador, features que ele recebe, em ordem)."""
        ...


def ler_features(conteudo: bytes | None) -> tuple[str, ...]:
    """A lista do features.json; sem o arquivo (versões anteriores a ele),
    as FEATURES fixas."""
    if conteudo is None:
        return FEATURES
    nomes = json.loads(conteudo)
    if not isinstance(nomes, list) or not all(
        isinstance(n, str) for n in nomes
    ):
        raise SemModeloError("features.json precisa ser uma lista de nomes")
    return tuple(nomes)


class Registry:
    """Versões e artefatos no Vertex AI Model Registry, pela API REST."""

    def __init__(
        self,
        projeto: str | None,
        regiao: str,
        alias: str,
        sessao: Any = None,
    ) -> None:
        self.projeto = projeto
        self.regiao = regiao
        self.api = f"https://{regiao}-aiplatform.googleapis.com/v1"
        self._alias = alias
        self._sessao = sessao

    @property
    def local(self) -> str:
        if not self.projeto:
            raise SemModeloError("MODELO_PROJECT_ID ausente")
        return f"projects/{self.projeto}/locations/{self.regiao}"

    def modelo_pai(self, nome: str) -> str | None:
        """Resource name do modelo (uma entrada por display_name), ou None."""
        resp = self.http().get(
            f"{self.api}/{self.local}/models",
            params={"filter": f'display_name="{nome}"'},
            timeout=REGISTRY_TIMEOUT_S,
        )
        resp.raise_for_status()
        encontrados = resp.json().get("models", [])
        return encontrados[0]["name"] if encontrados else None

    def com_alias(self, pai: str, alias: str) -> dict | None:
        """A versão do modelo com o alias, ou None."""
        resp = self.http().get(
            f"{self.api}/{pai}@{alias}", timeout=REGISTRY_TIMEOUT_S
        )
        if resp.status_code in (400, 404):
            return None
        resp.raise_for_status()
        return resp.json()

    def versao(self, nome: str) -> tuple[str, str]:
        pai = self.modelo_pai(nome)
        if pai is None:
            raise SemCampeaoError(f"{nome} não está no Model Registry")
        # Só a versão promovida: o alias `default` pode ser uma reprovada
        versao = self.com_alias(pai, self._alias)
        if versao is None:
            raise SemCampeaoError(f"{nome}: nenhuma versão com {self._alias}")
        return str(versao["versionId"]), versao["artifactUri"]

    def carregar(self, uri: str) -> tuple[Any, tuple[str, ...]]:
        import joblib
        from google.cloud import storage

        bucket, _, pasta = uri.removeprefix("gs://").partition("/")
        destino = storage.Client(project=self.projeto).bucket(bucket)

        def blob(nome: str) -> Any:
            return destino.blob(
                "/".join(p for p in (pasta.strip("/"), nome) if p)
            )

        estimador = joblib.load(
            io.BytesIO(blob("model.joblib").download_as_bytes())
        )
        lista = blob("features.json")
        return estimador, ler_features(
            lista.download_as_bytes() if lista.exists() else None
        )

    def http(self) -> Any:
        """Sessão autenticada com as credenciais padrão (ADC)."""
        if self._sessao is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credenciais, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self._sessao = AuthorizedSession(credenciais)
        return self._sessao


class PastaLocal:
    """<pasta>/<display_name>/model.joblib, para rodar sem o Registry."""

    def __init__(self, pasta: str) -> None:
        self._pasta = Path(pasta)

    def versao(self, nome: str) -> tuple[str, str]:
        arquivo = self._pasta / nome / "model.joblib"
        if not arquivo.exists():
            raise SemCampeaoError(f"{arquivo} não existe")
        return f"local-{int(arquivo.stat().st_mtime)}", str(arquivo)

    def carregar(self, uri: str) -> tuple[Any, tuple[str, ...]]:
        import joblib

        lista = Path(uri).with_name("features.json")
        return joblib.load(uri), ler_features(
            lista.read_bytes() if lista.exists() else None
        )


def validar(estimador: Any, features: Sequence[str] = FEATURES) -> Any:
    """Recusa na carga o que o /predict não conseguiria usar."""
    classes = {str(c) for c in getattr(estimador, "classes_", ())}
    if not hasattr(estimador, "predict_proba") or classes != set(CLASSES):
        raise SemModeloError(
            f"o modelo precisa de predict_proba e classes_ {CLASSES}, "
            f"tem {sorted(classes)}"
        )
    esperadas = getattr(estimador, "n_features_in_", len(features))
    if esperadas != len(features):
        raise SemModeloError(
            f"o modelo espera {esperadas} features, a lista tem {len(features)}"
        )
    return estimador


class Modelos:
    """O modelo de cada liga, com a versão conferida a cada `recarregar_s`.

    Promover outra versão no Registry (mover o alias) troca o modelo sem
    novo deploy. Se o Registry falhar, segue com a versão que já tem; se o
    alias sumir, para de servir a liga.
    """

    def __init__(
        self,
        fonte: Fonte,
        recarregar_s: float,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self._fonte = fonte
        self._recarregar_s = recarregar_s
        self._relogio = relogio
        self._trava = threading.Lock()
        # Uma trava por liga: um Registry lento numa liga não segura as outras
        self._travas: dict[str, threading.Lock] = {}
        self._atual: dict[str, Modelo] = {}
        self._conferido: dict[str, float] = {}
        self._sem_campeao: set[str] = set()

    def versao(self, liga: Liga) -> str | None:
        modelo = self._atual.get(liga.modelo)
        return modelo.versao if modelo else None

    def sem_campeao(self, liga: Liga) -> bool:
        return liga.modelo in self._sem_campeao

    def _trava_da(self, liga: Liga) -> threading.Lock:
        with self._trava:
            return self._travas.setdefault(liga.modelo, threading.Lock())

    def obter(self, liga: Liga) -> Modelo:
        with self._trava_da(liga):
            atual = self._atual.get(liga.modelo)
            conferido = self._conferido.get(liga.modelo)
            fresco = (
                conferido is not None
                and self._relogio() - conferido < self._recarregar_s
            )
            if fresco and atual is not None:
                return atual
            if fresco and liga.modelo in self._sem_campeao:
                # A resposta negativa também vale até a próxima conferência
                raise SemCampeaoError(f"{liga.modelo}: sem versão promovida")
            try:
                versao, uri = self._fonte.versao(liga.modelo)
                if atual is None or atual.versao != versao:
                    estimador, nomes = self._fonte.carregar(uri)
                    atual = Modelo(validar(estimador, nomes), versao, nomes)
                    log.info("%s: versão %s (%s)", liga.modelo, versao, uri)
            except SemCampeaoError:
                self._atual.pop(liga.modelo, None)
                self._sem_campeao.add(liga.modelo)
                self._conferido[liga.modelo] = self._relogio()
                raise
            except Exception as erro:
                if atual is None:
                    raise SemModeloError(f"{liga.modelo}: {erro}") from erro
                log.warning(
                    "%s: segue na versão %s (%s)",
                    liga.modelo,
                    atual.versao,
                    erro,
                )
            self._atual[liga.modelo] = atual
            self._sem_campeao.discard(liga.modelo)
            self._conferido[liga.modelo] = self._relogio()
            return atual


def fonte_padrao(cfg: Config) -> Fonte:
    if cfg.modelos_dir:
        return PastaLocal(cfg.modelos_dir)
    return Registry(cfg.projeto, cfg.regiao, cfg.alias)
