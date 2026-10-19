#!/usr/bin/env python3
"""Treina o modelo de cada liga e o registra no Vertex AI Model Registry.

Para cada liga de api.LIGAS, sobre a gold pública que a API também lê:

  1. separa por `split_set` as partidas com histórico completo e resultado;
  2. escolhe profundidade, taxa de aprendizado e número de árvores de um
     HistGradientBoostingClassifier pela log loss em EVAL;
  3. retreina em TRAIN + EVAL com o que venceu: a temporada de EVAL é a mais
     próxima das partidas que vamos prever;
  4. mede em TEST, que não entra em nenhuma escolha, contra os baselines
     sempre mandante (acurácia) e frequências do treino (log loss), e contra o
     modelo que a API serve hoje, reavaliado no mesmo TEST;
  5. aprovado nos três, sobe o artefato, registra uma versão nova e move o
     alias `campeao` para ela. A API troca de versão em até 10 minutos.

  uv run --no-project --with-requirements modelo/requirements.txt \\
      python modelo/treinar.py
  ... python modelo/treinar.py --ligas epl --sem-registrar --saida modelos/

Lê MODELO_PROJECT_ID (ou GCP_PROJECT_ID) e MODELOS_BUCKET do ambiente ou do
.env da raiz. Com --saida, grava <saida>/<modelo>/model.joblib, que a API usa
com MODELOS_DIR=<saida>.
"""

from __future__ import annotations

import argparse
import io
import itertools
import json
import math
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import api


ALIAS = "campeao"
# Só metadado: a API serve do Cloud Run. É o contêiner do Vertex para o
# scikit-learn de requirements.txt, caso alguém queira um endpoint.
SERVING = "us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-6:latest"
GRADE = {"max_depth": (2, 3, 4), "learning_rate": (0.03, 0.1)}
MAX_ARVORES = 300


@dataclass
class Conjunto:
    x: list[list[float]] = field(default_factory=list)
    y: list[str] = field(default_factory=list)


def separar(linhas: list[dict]) -> dict[str, Conjunto]:
    """TRAIN, EVAL e TEST só com partidas que têm histórico e resultado: sem
    os cinco jogos anteriores as janelas da gold ficam vazias."""
    conjuntos = {nome: Conjunto() for nome in ("TRAIN", "EVAL", "TEST")}
    for linha in linhas:
        conjunto = conjuntos.get(linha["split_set"])
        if (
            conjunto is None
            or not linha["has_full_history"]
            or linha["label_outcome"] not in api.CLASSES
        ):
            continue
        conjunto.x.append(api.vetor(linha))
        conjunto.y.append(linha["label_outcome"])
    return conjuntos


def metricas(y: list[str], probs: list[dict]) -> dict:
    """Acurácia, log loss e Brier multiclasse."""
    n = len(y)
    acertos = sum(
        max(api.CLASSES, key=p.__getitem__) == real
        for real, p in zip(y, probs, strict=True)
    )
    log_loss = -sum(
        math.log(max(p[real], 1e-15)) for real, p in zip(y, probs, strict=True)
    )
    brier = sum(
        sum((p[c] - (c == real)) ** 2 for c in api.CLASSES)
        for real, p in zip(y, probs, strict=True)
    )
    return {
        "n": n,
        "acuracia": acertos / n,
        "log_loss": log_loss / n,
        "brier": brier / n,
    }


def frequencias(y: list[str]) -> dict[str, float]:
    contagem = Counter(y)
    return {c: contagem[c] / len(y) for c in api.CLASSES}


def classificador(**params: Any) -> Any:
    from sklearn.ensemble import HistGradientBoostingClassifier

    # Sem early_stopping: ele separaria uma validação aleatória, misturando
    # temporadas. A parada é escolhida em EVAL, por data.
    return HistGradientBoostingClassifier(
        early_stopping=False, random_state=0, **params
    )


def escolher(
    treino: Conjunto,
    avaliacao: Conjunto,
    grade: dict = GRADE,
    maximo: int = MAX_ARVORES,
) -> tuple[dict, float]:
    """Os hiperparâmetros com a menor log loss em EVAL. Um ajuste por
    combinação: staged_predict_proba dá a predição depois de cada rodada de
    árvores, e daí sai o número de árvores."""
    melhor: dict = {}
    melhor_perda = math.inf
    for profundidade, taxa in itertools.product(
        grade["max_depth"], grade["learning_rate"]
    ):
        modelo = classificador(
            max_depth=profundidade, learning_rate=taxa, max_iter=maximo
        ).fit(treino.x, treino.y)
        classes = [str(c) for c in modelo.classes_]
        estagios = modelo.staged_predict_proba(avaliacao.x)
        for arvores, proba in enumerate(estagios, start=1):
            probs = [dict(zip(classes, linha, strict=True)) for linha in proba]
            perda = metricas(avaliacao.y, probs)["log_loss"]
            if perda < melhor_perda:
                melhor_perda = perda
                melhor = {
                    "max_depth": profundidade,
                    "learning_rate": taxa,
                    "max_iter": arvores,
                }
    return melhor, melhor_perda


def decidir(
    modelo: dict, mandante: float, freq: dict, campeao: dict | None
) -> list[str]:
    """Motivos para reprovar; vazio = aprovado."""
    motivos = []
    if modelo["acuracia"] <= mandante:
        motivos.append(
            f"acurácia {modelo['acuracia']:.4f} não passa sempre mandante "
            f"({mandante:.4f})"
        )
    if modelo["log_loss"] >= freq["log_loss"]:
        motivos.append(
            f"log loss {modelo['log_loss']:.4f} não passa as frequências "
            f"({freq['log_loss']:.4f})"
        )
    if campeao is not None and modelo["log_loss"] >= campeao["log_loss"]:
        motivos.append(
            f"log loss {modelo['log_loss']:.4f} não passa o campeão "
            f"({campeao['log_loss']:.4f})"
        )
    return motivos


def treinar_liga(
    liga: api.Liga,
    linhas: list[dict],
    atual: Callable[[api.Liga], tuple[str, Any] | None],
    **busca: Any,
) -> tuple[Any, dict]:
    """(estimador, relatório). `atual` devolve (versão, estimador) do modelo
    que a API serve hoje, ou None."""
    conjuntos = separar(linhas)
    treino, avaliacao, teste = (
        conjuntos["TRAIN"],
        conjuntos["EVAL"],
        conjuntos["TEST"],
    )
    params, perda_eval = escolher(treino, avaliacao, **busca)
    final = Conjunto(treino.x + avaliacao.x, treino.y + avaliacao.y)
    estimador = classificador(**params).fit(final.x, final.y)
    api.validar(estimador)

    modelo = metricas(teste.y, api.probabilidades(estimador, teste.x))
    mandante = sum(r == "home" for r in teste.y) / len(teste.y)
    priori = frequencias(final.y)
    freq = metricas(teste.y, [priori] * len(teste.y))
    campeao = None
    versao_atual = atual(liga)
    if versao_atual is not None:
        versao, estimador_atual = versao_atual
        probs = api.probabilidades(estimador_atual, teste.x)
        campeao = {"versao": versao, **metricas(teste.y, probs)}
    motivos = decidir(modelo, mandante, freq, campeao)

    from sklearn import __version__ as sklearn

    relatorio = {
        "liga": liga.league_id,
        "modelo": liga.modelo,
        "scikit_learn": sklearn,
        "features": list(api.FEATURES),
        "partidas": {nome: len(c.y) for nome, c in conjuntos.items()},
        "hiperparametros": params,
        "log_loss_eval": perda_eval,
        "teste": {
            "modelo": modelo,
            "sempre_mandante": {"acuracia": mandante},
            "frequencias": freq,
            "campeao": campeao,
        },
        "aprovado": not motivos,
        "motivos": motivos,
    }
    return estimador, relatorio


def imprimir(relatorio: dict) -> None:
    p = relatorio["partidas"]
    h = relatorio["hiperparametros"]
    t = relatorio["teste"]
    print(f"\n== {relatorio['modelo']} ({relatorio['liga']})")
    print(f"partidas: TRAIN {p['TRAIN']}, EVAL {p['EVAL']}, TEST {p['TEST']}")
    print(
        f"escolhido em EVAL (log loss {relatorio['log_loss_eval']:.4f}): "
        f"max_depth={h['max_depth']}, learning_rate={h['learning_rate']}, "
        f"max_iter={h['max_iter']}; retreinado em TRAIN+EVAL"
    )
    print(f"{'TEST':<22}{'acurácia':>10}{'log loss':>10}{'brier':>8}")
    linhas = [
        ("modelo", t["modelo"]),
        ("sempre mandante", t["sempre_mandante"]),
        ("frequências", t["frequencias"]),
    ]
    if t["campeao"]:
        linhas.append(
            (f"campeão atual (v{t['campeao']['versao']})", t["campeao"])
        )
    for nome, m in linhas:
        valores = [m.get(k) for k in ("acuracia", "log_loss", "brier")]
        celulas = ["-" if v is None else f"{v:.4f}" for v in valores]
        print(f"  {nome:<20}{celulas[0]:>10}{celulas[1]:>10}{celulas[2]:>8}")
    if relatorio["aprovado"]:
        print("decisão: aprovado")
    else:
        print("decisão: reprovado; " + "; ".join(relatorio["motivos"]))


# --- Registry ---------------------------------------------------------------


def subir(
    projeto: str, bucket: str, regiao: str, pasta: str, arquivos: dict
) -> str:
    """Grava os arquivos em gs://<bucket>/<pasta>/ (cria o bucket na região
    do Registry se faltar) e devolve a URI do diretório."""
    from google.cloud import storage

    cliente = storage.Client(project=projeto)
    destino = cliente.bucket(bucket)
    if not destino.exists():
        destino.iam_configuration.uniform_bucket_level_access_enabled = True
        destino.iam_configuration.public_access_prevention = "enforced"
        destino = cliente.create_bucket(destino, location=regiao)
    for nome, conteudo in arquivos.items():
        destino.blob(f"{pasta}/{nome}").upload_from_string(conteudo)
    return f"gs://{bucket}/{pasta}/"


def registrar(
    registry: api.Registry,
    nome: str,
    uri: str,
    descricao: str,
    rotulos: dict[str, str],
) -> tuple[str, str]:
    """Registra o diretório como versão nova do modelo (ou cria o modelo).
    Devolve (resource name do modelo, versão)."""
    pai = registry.modelo_pai(nome)
    corpo: dict[str, Any] = {
        "model": {
            "displayName": nome,
            "artifactUri": uri,
            "containerSpec": {"imageUri": SERVING},
            "versionDescription": descricao[:1000],
            "labels": rotulos,
        }
    }
    if pai:
        corpo["parentModel"] = pai
    http = registry.http()
    resp = http.post(
        f"{registry.api}/{registry.local}/models:upload", json=corpo
    )
    resp.raise_for_status()
    operacao = resp.json()
    while not operacao.get("done"):
        time.sleep(2)
        resp = http.get(f"{registry.api}/{operacao['name']}")
        resp.raise_for_status()
        operacao = resp.json()
    if "error" in operacao:
        raise RuntimeError(f"upload de {nome}: {operacao['error']}")
    resposta = operacao["response"]
    return resposta["model"], str(resposta["modelVersionId"])


def promover(
    registry: api.Registry, pai: str, versao: str, alias: str = ALIAS
) -> str | None:
    """Move o alias para a versão (um alias é único por modelo). Devolve a
    versão que tinha o alias antes, ou None."""
    atual = registry.com_alias(pai, alias)
    anterior = str(atual["versionId"]) if atual else None
    if anterior == versao:
        return anterior
    if anterior is not None:
        _aliases(registry, pai, anterior, [f"-{alias}"])
    _aliases(registry, pai, versao, [alias])
    return anterior


def _aliases(
    registry: api.Registry, pai: str, versao: str, aliases: list[str]
) -> None:
    resp = registry.http().post(
        f"{registry.api}/{pai}@{versao}:mergeVersionAliases",
        json={"versionAliases": aliases},
    )
    resp.raise_for_status()


def modelo_atual(
    registry: api.Registry | None, tolerar: bool = False
) -> Callable[[api.Liga], tuple[str, Any] | None]:
    """(versão, estimador) que a API serve hoje para a liga, ou None. Com
    `tolerar`, uma falha no Registry só pula a comparação (o --sem-registrar
    roda sem credenciais); registrando, ela para o treino, para nunca
    promover sem comparar com o campeão."""

    def atual(liga: api.Liga) -> tuple[str, Any] | None:
        if registry is None:
            return None
        try:
            versao, uri = registry.versao(liga.modelo)
            return versao, registry.carregar(uri)
        except api.SemModeloError:
            return None
        except Exception as erro:
            if not tolerar:
                raise
            print(f"aviso: campeão de {liga.modelo} não lido: {erro}")
            return None

    return atual


def main(argv: list[str] | None = None) -> int:
    cfg = api.Config.do_ambiente()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--ligas", nargs="+", choices=sorted(api.LIGAS), default=list(api.LIGAS)
    )
    parser.add_argument(
        "--sem-registrar",
        action="store_true",
        help="treina e avalia, sem subir nem registrar nada",
    )
    parser.add_argument("--saida", type=Path, help="grava o model.joblib aqui")
    parser.add_argument(
        "--bucket",
        default=api.ambiente().get("MODELOS_BUCKET")
        or (f"{cfg.projeto}-modelos" if cfg.projeto else None),
    )
    args = parser.parse_args(argv)

    if not args.sem_registrar and not (cfg.projeto and args.bucket):
        parser.error("MODELO_PROJECT_ID ausente (ou use --sem-registrar)")
    registry = (
        api.Registry(cfg.projeto, cfg.regiao, ALIAS) if cfg.projeto else None
    )
    carimbo = datetime.now(UTC).strftime("%Y%m%dt%H%M%Sz")
    reprovadas = 0
    for liga_id in args.ligas:
        liga = api.LIGAS[liga_id]
        url = f"{cfg.dados_url.rstrip('/')}/{liga.gold}"
        colunas = [*api.COLUNAS, "label_outcome", "split_set"]
        linhas = api.ler_parquet(api.baixar_publico(url), colunas)
        estimador, relatorio = treinar_liga(
            liga, linhas, modelo_atual(registry, tolerar=args.sem_registrar)
        )
        relatorio["execucao"] = carimbo
        imprimir(relatorio)

        import joblib

        artefato = io.BytesIO()
        joblib.dump(estimador, artefato)
        arquivos = {
            "model.joblib": artefato.getvalue(),
            "metricas.json": json.dumps(
                relatorio, indent=2, ensure_ascii=False
            ).encode(),
        }
        if args.saida:
            pasta = args.saida / liga.modelo
            pasta.mkdir(parents=True, exist_ok=True)
            for nome, conteudo in arquivos.items():
                (pasta / nome).write_bytes(conteudo)
            print(f"gravado em {pasta}")

        if not relatorio["aprovado"]:
            reprovadas += 1
            continue
        if args.sem_registrar or registry is None:
            continue
        uri = subir(
            cfg.projeto or "",
            args.bucket,
            cfg.regiao,
            f"{liga.modelo}/{carimbo}",
            arquivos,
        )
        m = relatorio["teste"]["modelo"]
        descricao = (
            f"{carimbo} | TEST n={m['n']} acurácia {m['acuracia']:.4f} "
            f"log loss {m['log_loss']:.4f} | {relatorio['hiperparametros']}"
        )
        rotulos = {
            "liga": liga.league_id,
            "execucao": carimbo,
            "origem": "treinar_py",
        }
        pai, versao = registrar(registry, liga.modelo, uri, descricao, rotulos)
        anterior = promover(registry, pai, versao)
        print(
            f"registrado: {liga.modelo} versão {versao} ({uri}); "
            f"alias {ALIAS}: {anterior or 'nenhuma'} -> {versao}"
        )
    return 1 if reprovadas else 0


if __name__ == "__main__":
    sys.exit(main())
