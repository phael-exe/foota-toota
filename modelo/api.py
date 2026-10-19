#!/usr/bin/env python3
"""API do modelo do Trabalho 2: prevê o resultado das partidas.

Um serviço Cloud Run com as rotas da seção 4 de docs/trabalho2/contratos.md,
que chamam a mesma função de predição:

  POST /predict  {"match_id": "fdorg_555047"}: devolve a predição no formato
                 da seção 3 e a publica no tópico `predicoes`
  POST /pubsub   push da assinatura `eventos-api`: prevê as partidas
                 agendadas, publica em `predicoes` e responde 204. Com
                 TABELA_AVALIACAO, grava também predição e resultado real
                 numa linha por match_id (modelo/sql/predicoes_vs_real.sql)
  GET  /health   versão do modelo e partidas carregadas de cada liga

Features: a gold pública de cada liga (gs://foota-toota-505511/gold/), relida
a cada RECARREGAR_SEGUNDOS. A partida é achada pelo match_id e, se não estiver
lá, pelo confronto (temporada, mandante, visitante): o replay do Brasileirão
traz ids `fdorg_` de jogos que a gold guarda com o id de outra fonte, e o
de-para de clubes sai do bronze público do Football-Data.org.

Modelos: um por liga no Vertex AI Model Registry de MODELO_PROJECT_ID, com o
display_name da tabela LIGAS. Vale a versão com o alias `campeao` (ou a
padrão), conferida a cada RECARREGAR_SEGUNDOS. O artefato é o `model.joblib`
do diretório da versão:

  - um estimador scikit-learn com predict_proba e classes_ iguais a
    {"home", "draw", "away"} (os rótulos de silver.matches.outcome);
  - entrada = array posicional na ordem de FEATURES, NaN onde falta dado;
  - treinado com o scikit-learn de modelo/requirements.txt.

Sem o Registry, MODELOS_DIR aponta uma pasta com <display_name>/model.joblib.

  cd modelo && uvicorn api:app --port 8080
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Protocol

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel


RAIZ = Path(__file__).resolve().parent.parent
PIPELINE = "pdm-bia-505511"
DADOS = "https://storage.googleapis.com/foota-toota-505511"
CLASSES = ("home", "draw", "away")
AGENDADA = {"TIMED", "SCHEDULED"}

# Ordem canônica: a do SELECT do T1 (sql/06_model) e do array que o modelo
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
COLUNAS = [
    "match_id",
    "league_id",
    "season",
    "home_team_id",
    "away_team_id",
    "has_full_history",
    *FEATURES,
]

log = logging.getLogger("modelo")


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
    topico: str = f"projects/{PIPELINE}/topics/predicoes"
    dados_url: str = DADOS
    push_sa: str = f"pubsub-push@{PIPELINE}.iam.gserviceaccount.com"
    push_audience: str | None = None
    verificar_token: bool = True
    modelos_dir: str | None = None
    recarregar_s: float = 600.0
    tabela_avaliacao: str | None = None  # projeto.dataset.tabela

    @classmethod
    def do_ambiente(cls) -> Config:
        env = ambiente()
        return cls(
            projeto=env.get("MODELO_PROJECT_ID") or env.get("GCP_PROJECT_ID"),
            regiao=env.get("MODELO_REGIAO", cls.regiao),
            alias=env.get("ALIAS_MODELO", cls.alias),
            topico=env.get("TOPICO_PREDICOES", cls.topico),
            dados_url=env.get("DADOS_URL", cls.dados_url),
            push_sa=env.get("PUSH_SA", cls.push_sa),
            push_audience=env.get("PUSH_AUDIENCE") or None,
            verificar_token=env.get("VERIFICAR_TOKEN", "1") != "0",
            modelos_dir=env.get("MODELOS_DIR") or None,
            recarregar_s=float(env.get("RECARREGAR_SEGUNDOS", "600")),
            tabela_avaliacao=env.get("TABELA_AVALIACAO") or None,
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


# --- features ---------------------------------------------------------------


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


# --- modelos ----------------------------------------------------------------


class SemModeloError(Exception):
    """A liga não tem modelo utilizável no Registry (ou na pasta local)."""


@dataclass(frozen=True)
class Modelo:
    estimador: Any
    versao: str


class Fonte(Protocol):
    def versao(self, nome: str) -> tuple[str, str]:
        """(version_id, uri do artefato) da versão que vale agora."""
        ...

    def carregar(self, uri: str) -> Any: ...


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
        )
        resp.raise_for_status()
        encontrados = resp.json().get("models", [])
        return encontrados[0]["name"] if encontrados else None

    def com_alias(self, pai: str, alias: str) -> dict | None:
        """A versão do modelo com o alias, ou None."""
        resp = self.http().get(f"{self.api}/{pai}@{alias}")
        if resp.status_code in (400, 404):
            return None
        resp.raise_for_status()
        return resp.json()

    def versao(self, nome: str) -> tuple[str, str]:
        pai = self.modelo_pai(nome)
        if pai is None:
            raise SemModeloError(f"{nome} não está no Model Registry")
        for alias in (self._alias, "default"):
            versao = self.com_alias(pai, alias)
            if versao is not None:
                return str(versao["versionId"]), versao["artifactUri"]
        raise SemModeloError(f"{nome}: nenhuma versão com alias")

    def carregar(self, uri: str) -> Any:
        import joblib
        from google.cloud import storage

        bucket, _, pasta = uri.removeprefix("gs://").partition("/")
        caminho = "/".join(p for p in (pasta.strip("/"), "model.joblib") if p)
        blob = storage.Client(project=self.projeto).bucket(bucket).blob(caminho)
        return joblib.load(io.BytesIO(blob.download_as_bytes()))

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
            raise SemModeloError(f"{arquivo} não existe")
        return f"local-{int(arquivo.stat().st_mtime)}", str(arquivo)

    def carregar(self, uri: str) -> Any:
        import joblib

        return joblib.load(uri)


def validar(estimador: Any) -> Any:
    """Recusa na carga o que o /predict não conseguiria usar."""
    classes = {str(c) for c in getattr(estimador, "classes_", ())}
    if not hasattr(estimador, "predict_proba") or classes != set(CLASSES):
        raise SemModeloError(
            f"o modelo precisa de predict_proba e classes_ {CLASSES}, "
            f"tem {sorted(classes)}"
        )
    esperadas = getattr(estimador, "n_features_in_", len(FEATURES))
    if esperadas != len(FEATURES):
        raise SemModeloError(
            f"o modelo espera {esperadas} features, a API manda {len(FEATURES)}"
        )
    return estimador


class Modelos:
    """O modelo de cada liga, com a versão conferida a cada `recarregar_s`.

    Promover outra versão no Registry (mover o alias) troca o modelo sem
    novo deploy. Se o Registry falhar, segue com a versão que já tem.
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
        self._atual: dict[str, Modelo] = {}
        self._conferido: dict[str, float] = {}

    def versao(self, liga: Liga) -> str | None:
        modelo = self._atual.get(liga.modelo)
        return modelo.versao if modelo else None

    def obter(self, liga: Liga) -> Modelo:
        with self._trava:
            atual = self._atual.get(liga.modelo)
            conferido = self._conferido.get(liga.modelo)
            if (
                atual is not None
                and conferido is not None
                and self._relogio() - conferido < self._recarregar_s
            ):
                return atual
            try:
                versao, uri = self._fonte.versao(liga.modelo)
                if atual is None or atual.versao != versao:
                    atual = Modelo(validar(self._fonte.carregar(uri)), versao)
                    log.info("%s: versão %s (%s)", liga.modelo, versao, uri)
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
            self._conferido[liga.modelo] = self._relogio()
            return atual


def fonte_padrao(cfg: Config) -> Fonte:
    if cfg.modelos_dir:
        return PastaLocal(cfg.modelos_dir)
    return Registry(cfg.projeto, cfg.regiao, cfg.alias)


# --- predição ---------------------------------------------------------------


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


# --- Pub/Sub ----------------------------------------------------------------


def publicador(topico: str) -> Callable[[dict], None]:
    cliente: Any = None

    def publicar(mensagem: dict) -> None:
        nonlocal cliente
        if cliente is None:
            from google.cloud import pubsub_v1

            cliente = pubsub_v1.PublisherClient()
        corpo = json.dumps(mensagem, ensure_ascii=False).encode()
        cliente.publish(topico, corpo).result(timeout=30)

    return publicar


def verificador(cfg: Config) -> Callable[[str | None], None]:
    """Confere o token OIDC do push (seção 6 do contrato): assinado pelo
    Google, da conta pubsub-push e com audience = URL do /pubsub."""

    def verificar(autorizacao: str | None) -> None:
        if not cfg.verificar_token:
            return
        if not autorizacao or not autorizacao.startswith("Bearer "):
            raise HTTPException(401, "token do push ausente")
        if not cfg.push_audience:
            # 5xx: o Pub/Sub guarda a mensagem até a API ser configurada
            raise HTTPException(500, "PUSH_AUDIENCE não configurado")
        from google.auth.transport import requests
        from google.oauth2 import id_token

        try:
            dados = id_token.verify_oauth2_token(
                autorizacao.removeprefix("Bearer "),
                requests.Request(),
                audience=cfg.push_audience,
            )
        except ValueError as erro:
            raise HTTPException(401, f"token inválido: {erro}") from erro
        if dados.get("email") != cfg.push_sa or not dados.get("email_verified"):
            raise HTTPException(403, "push de outra conta")

    return verificar


class Recentes:
    """Últimos event_ids já previstos nesta instância: o Pub/Sub entrega
    pelo menos uma vez."""

    def __init__(self, limite: int = 10_000) -> None:
        self._limite = limite
        self._itens: OrderedDict[str, None] = OrderedDict()
        self._trava = threading.Lock()

    def __contains__(self, chave: object) -> bool:
        with self._trava:
            return chave in self._itens

    def adicionar(self, chave: str) -> None:
        with self._trava:
            self._itens[chave] = None
            self._itens.move_to_end(chave)
            while len(self._itens) > self._limite:
                self._itens.popitem(last=False)


def ler_evento(corpo: bytes) -> dict:
    """O evento dentro do envelope do push (base64 em message.data)."""
    envelope = json.loads(corpo)
    evento = json.loads(base64.b64decode(envelope["message"]["data"]))
    if not isinstance(evento, dict) or not evento.get("match_id"):
        raise ValueError("evento sem match_id")
    return evento


# --- predição x real --------------------------------------------------------


def resultado_real(evento: dict) -> str | None:
    """home, draw ou away pelo placar final; None sem placar."""
    casa, fora = evento.get("score_home"), evento.get("score_away")
    if casa is None or fora is None:
        return None
    if casa > fora:
        return "home"
    return "draw" if casa == fora else "away"


def _instante(valor: Any) -> datetime | None:
    """ISO 8601 (com Z) para datetime, como o parâmetro TIMESTAMP pede."""
    if not valor:
        return None
    return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))


class Avaliacao:
    """Tabela predição x real no BigQuery (modelo/sql/predicoes_vs_real.sql),
    uma linha por match_id: o id do evento é o mesmo antes e depois do jogo.

    A predição e o resultado chegam em qualquer ordem (o Pub/Sub não garante
    ordem e reentrega), então os dois lados fazem MERGE: quem chega primeiro
    cria a linha, quem chega depois completa e calcula o acerto."""

    CONTEXTO = (
        "league_id",
        "competition",
        "season",
        "matchday",
        "kickoff_utc",
        "home_team_id",
        "home_team_name",
        "away_team_id",
        "away_team_name",
        "mode",
    )
    PREDICAO = (
        "prediction_id",
        "event_id",
        "model_name",
        "model_version",
        "prob_home",
        "prob_draw",
        "prob_away",
        "predicted_outcome",
        "predicted_at",
    )
    RESULTADO = (
        "score_home",
        "score_away",
        "real_outcome",
        "result_event_id",
        "result_at",
    )
    TIPOS: ClassVar[dict[str, str]] = {
        "season": "INT64",
        "matchday": "INT64",
        "score_home": "INT64",
        "score_away": "INT64",
        "prob_home": "FLOAT64",
        "prob_draw": "FLOAT64",
        "prob_away": "FLOAT64",
        "kickoff_utc": "TIMESTAMP",
        "predicted_at": "TIMESTAMP",
        "result_at": "TIMESTAMP",
    }

    def __init__(self, tabela: str, cliente: Any = None) -> None:
        self.tabela = tabela
        self._cliente = cliente

    def predicao(self, liga: Liga, evento: dict, mensagem: dict) -> None:
        valores = {c: mensagem[c] for c in self.PREDICAO}
        self._merge(
            liga,
            evento,
            valores,
            "IF(t.real_outcome IS NULL, NULL,"
            " s.predicted_outcome = t.real_outcome)",
        )

    def resultado(self, liga: Liga, evento: dict) -> None:
        valores = {
            "score_home": evento.get("score_home"),
            "score_away": evento.get("score_away"),
            "real_outcome": resultado_real(evento),
            "result_event_id": evento.get("event_id"),
            "result_at": evento.get("source_updated_at")
            or evento.get("published_at"),
        }
        self._merge(
            liga,
            evento,
            valores,
            "IF(t.predicted_outcome IS NULL, NULL,"
            " t.predicted_outcome = s.real_outcome)",
        )

    def _merge(
        self, liga: Liga, evento: dict, proprios: dict, acerto: str
    ) -> None:
        from google.cloud import bigquery

        contexto = {c: evento.get(c) for c in self.CONTEXTO}
        contexto["league_id"] = liga.league_id
        valores = {"match_id": evento["match_id"], **contexto, **proprios}
        parametros = [
            bigquery.ScalarQueryParameter(
                nome,
                self.TIPOS.get(nome, "STRING"),
                _instante(valor)
                if self.TIPOS.get(nome) == "TIMESTAMP"
                else valor,
            )
            for nome, valor in valores.items()
        ]
        fonte = ", ".join(f"@{nome} AS {nome}" for nome in valores)
        # O contexto do evento mais novo vence, sem apagar o que ele não traz
        atualiza = [f"{c} = COALESCE(s.{c}, t.{c})" for c in contexto]
        atualiza += [f"{c} = s.{c}" for c in proprios]
        colunas = ", ".join(valores)
        sql = f"""
            MERGE `{self.tabela}` t
            USING (SELECT {fonte}) s
            ON t.match_id = s.match_id
            WHEN MATCHED THEN UPDATE SET
                {", ".join(atualiza)},
                hit = {acerto},
                updated_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN
                INSERT ({colunas}, updated_at)
                VALUES ({", ".join(f"s.{c}" for c in valores)},
                        CURRENT_TIMESTAMP())
        """
        if self._cliente is None:
            self._cliente = bigquery.Client(project=self.tabela.split(".")[0])
        config = bigquery.QueryJobConfig(query_parameters=parametros)
        self._cliente.query(sql, job_config=config).result(timeout=50)


# --- rotas ------------------------------------------------------------------


class Pedido(BaseModel):
    match_id: str
    league_id: str | None = None
    # Features diretas, para simular uma partida: as que faltam viram NaN
    features: dict[str, float | None] | None = None
    publicar: bool = True


def criar_app(
    cfg: Config | None = None,
    *,
    features: dict[str, Features] | None = None,
    modelos: Modelos | None = None,
    publicar: Callable[[dict], None] | None = None,
    verificar: Callable[[str | None], None] | None = None,
    avaliacao: Avaliacao | None = None,
    relogio: Callable[[], str] = agora,
    aquecer: bool = False,
) -> FastAPI:
    cfg = cfg or Config.do_ambiente()
    if avaliacao is None and cfg.tabela_avaliacao:
        avaliacao = Avaliacao(cfg.tabela_avaliacao)
    if features is None:
        features = {
            liga.league_id: Features(liga, cfg.dados_url, cfg.recarregar_s)
            for liga in LIGAS.values()
        }
    lojas = features
    modelos_ = modelos or Modelos(fonte_padrao(cfg), cfg.recarregar_s)
    publicar_ = publicar or publicador(cfg.topico)
    verificar_ = verificar or verificador(cfg)
    vistos = Recentes()

    def aquecer_tudo() -> None:
        """Lê features e modelos antes do primeiro pedido, sem travar o
        início do serviço; o que falhar é lido de novo no primeiro uso."""
        for loja in lojas.values():
            try:
                loja.buscar("")
                modelos_.obter(loja.liga)
            except Exception as erro:
                log.warning("%s: aquecimento: %s", loja.liga.league_id, erro)

    @asynccontextmanager
    async def ciclo(_: FastAPI) -> AsyncIterator[None]:
        if aquecer:
            threading.Thread(target=aquecer_tudo, daemon=True).start()
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
            "predicoes_vs_real": avaliacao.tabela if avaliacao else None,
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
    def predict(pedido: Pedido, response: Response) -> dict:
        liga, linha = localizar(pedido)
        try:
            modelo = modelos_.obter(liga)
        except SemModeloError as erro:
            raise HTTPException(503, str(erro)) from erro
        mensagem = predicao(
            liga, modelo, linha, pedido.match_id, None, relogio()
        )
        if pedido.publicar:
            try:
                publicar_(mensagem)
                response.headers["X-Publicada"] = "true"
            except Exception:
                log.exception("%s não publicada", mensagem["prediction_id"])
                response.headers["X-Publicada"] = "false"
        return mensagem

    def processar(corpo: bytes) -> int:
        """Status da resposta ao push: 204 confirma (inclusive o que é
        ignorado de propósito); 503 pede reentrega numa falha passageira.

        Agendada: prevê, grava a predição na tabela predição x real e
        publica em `predicoes`. Encerrada: grava o resultado real na mesma
        linha (mesmo match_id). O resto é ignorado."""
        try:
            evento = ler_evento(corpo)
        except (ValueError, KeyError, TypeError) as erro:
            log.warning("mensagem ilegível descartada: %s", erro)
            return 204
        event_id = evento.get("event_id")
        status = evento.get("status")
        encerrada = status == "FINISHED" and avaliacao is not None
        if (status not in AGENDADA and not encerrada) or event_id in vistos:
            return 204
        loja = next(
            (
                loja
                for loja in lojas.values()
                if loja.liga.competicao == evento.get("competition")
            ),
            None,
        )
        if loja is None:
            return 204
        match_id = evento["match_id"]
        try:
            if encerrada and avaliacao is not None:
                avaliacao.resultado(loja.liga, evento)
                log.info("%s: resultado %s", match_id, resultado_real(evento))
            else:
                linha = loja.buscar(match_id, evento)
                if linha is None:
                    log.warning("%s não está na gold; ignorado", match_id)
                    return 204
                modelo = modelos_.obter(loja.liga)
                mensagem = predicao(
                    loja.liga, modelo, linha, match_id, event_id, relogio()
                )
                # Antes de publicar: se a gravação falhar, a reentrega refaz
                # as duas coisas, e o prediction_id é o mesmo
                if avaliacao is not None:
                    avaliacao.predicao(loja.liga, evento, mensagem)
                publicar_(mensagem)
                log.info(
                    "%s -> %s (%s v%s)",
                    match_id,
                    mensagem["predicted_outcome"],
                    mensagem["model_name"],
                    mensagem["model_version"],
                )
        except Exception:
            log.exception("%s: falha, o Pub/Sub tenta de novo", event_id)
            return 503
        if event_id:
            vistos.adicionar(event_id)
        return 204

    @app.post("/pubsub", status_code=204)
    async def pubsub(request: Request) -> Response:
        await run_in_threadpool(
            verificar_, request.headers.get("authorization")
        )
        status = await run_in_threadpool(processar, await request.body())
        return Response(status_code=status)

    return app


logging.basicConfig(
    level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
)
app = criar_app(aquecer=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
