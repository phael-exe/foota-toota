#!/usr/bin/env python3
"""Prevê de novo os jogos agendados dos próximos dias, com a gold de hoje.

O Dataflow prevê um jogo quando o coletor vê o jogo mudar, muitas vezes semanas
antes. As odds do mercado só aparecem 2 a 4 dias antes, e o Elo e a forma mudam
a cada rodada: sem esta passada, a predição que a plataforma mostra ficaria
presa à primeira. Roda no começo de scripts/atualizar_partidas.sh, quando a
API já carregou a gold da exportação anterior, e a exportação do fim leva as
predições novas (gold.predicoes junta stream.predicoes_lote).

  python3 scripts/repredizer.py            # próximos 7 dias
  python3 scripts/repredizer.py --dias 3

Lê GCP_PROJECT_ID do ambiente (ou do .env da raiz) e MODELO_API_URL (sem ele,
pergunta ao Cloud Run a URL do modelo-api). Só usa a biblioteca padrão, o httpx
e os comandos gcloud e bq, como o resto do Job do batch.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
LIGAS = ("brasileirao_serie_a", "epl")
LOTE_MAXIMO = 100
TABELA = "stream.predicoes_lote"
# Na ordem da tabela (sql/10_stream/09a_create_table_predicoes_lote.sql)
COLUNAS = (
    "prediction_id",
    "match_id",
    "league_id",
    "model_name",
    "model_version",
    "prob_home",
    "prob_draw",
    "prob_away",
    "predicted_outcome",
    "predicted_at",
    "kickoff_utc",
    "features_ate",
    "mode",
)


def consulta(projeto: str, dias: int) -> str:
    ligas = ", ".join(f"'{liga}'" for liga in LIGAS)
    return f"""
        SELECT
            match_id,
            league_id,
            FORMAT_TIMESTAMP('%F %T', kickoff_utc) AS kickoff_utc
        FROM `{projeto}.gold.match_features`
        WHERE status = 'scheduled'
          AND league_id IN ({ligas})
          AND kickoff_utc BETWEEN CURRENT_TIMESTAMP()
              AND TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL {int(dias)} DAY)
        ORDER BY kickoff_utc
    """


def lotes(jogos: list[dict], tamanho: int = LOTE_MAXIMO) -> list[list[dict]]:
    pedidos = [
        {"match_id": j["match_id"], "league_id": j["league_id"]} for j in jogos
    ]
    return [pedidos[i : i + tamanho] for i in range(0, len(pedidos), tamanho)]


def linhas(
    resultados: list[dict], jogos: dict[str, dict]
) -> tuple[list[dict], Counter]:
    """As linhas da tabela, das predições que deram certo, e a contagem das
    falhas por motivo (sem campeão, fora da gold...)."""
    saida, falhas = [], Counter()
    for item in resultados:
        predicao = item.get("predicao")
        if item.get("status") != 200 or not predicao:
            falhas[item.get("motivo") or f"http_{item.get('status')}"] += 1
            continue
        linha = {c: predicao.get(c) for c in COLUNAS}
        linha["kickoff_utc"] = jogos[item["match_id"]]["kickoff_utc"]
        linha["mode"] = "lote"
        saida.append(linha)
    return saida, falhas


# --- GCP --------------------------------------------------------------------


def ambiente() -> dict[str, str]:
    env = dict(os.environ)
    arquivo = RAIZ / ".env"
    if arquivo.exists():
        for texto in arquivo.read_text(encoding="utf-8").splitlines():
            if "=" in texto and not texto.lstrip().startswith("#"):
                chave, valor = texto.split("=", 1)
                env.setdefault(chave.strip(), valor.strip().strip("'\""))
    return env


def rodar(*comando: str) -> str:
    return subprocess.run(
        comando, check=True, capture_output=True, text=True
    ).stdout


def url_api(env: dict[str, str], projeto: str) -> str:
    if env.get("MODELO_API_URL"):
        return env["MODELO_API_URL"].rstrip("/")
    return rodar(
        "gcloud",
        "run",
        "services",
        "describe",
        "modelo-api",
        "--region=us-central1",
        f"--project={projeto}",
        "--format=value(status.url)",
    ).strip()


def token(audiencia: str) -> str:
    """No Cloud Run, o metadata server dá o token da conta do Job; na máquina,
    o gcloud dá o da conta logada."""
    import httpx

    try:
        resposta = httpx.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/"
            "service-accounts/default/identity",
            params={"audience": audiencia},
            headers={"Metadata-Flavor": "Google"},
            timeout=5.0,
        )
        resposta.raise_for_status()
        return resposta.text
    except httpx.HTTPError:
        return rodar("gcloud", "auth", "print-identity-token").strip()


def main(argv: list[str] | None = None) -> int:
    import httpx

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dias", type=int, default=7)
    args = parser.parse_args(argv)

    env = ambiente()
    projeto = env.get("GCP_PROJECT_ID")
    if not projeto:
        parser.error("GCP_PROJECT_ID ausente")
    saida_bq = rodar(
        "bq",
        f"--project_id={projeto}",
        "query",
        "--use_legacy_sql=false",
        "--format=json",
        "--max_rows=10000",
        consulta(projeto, args.dias),
    )
    jogos = {j["match_id"]: j for j in json.loads(saida_bq or "[]")}
    if not jogos:
        print(f"nenhum jogo agendado nos próximos {args.dias} dias")
        return 0

    url = url_api(env, projeto)
    cabecalho = {"Authorization": f"Bearer {token(url)}"}
    resultados = []
    with httpx.Client(timeout=120.0) as cliente:
        for lote in lotes(list(jogos.values())):
            resposta = cliente.post(
                f"{url}/predict/lote", json={"pedidos": lote}, headers=cabecalho
            )
            resposta.raise_for_status()
            resultados += resposta.json()["resultados"]

    novas, falhas = linhas(resultados, jogos)
    if falhas:
        print(
            f"aviso: {sum(falhas.values())} sem predição: {dict(falhas)}",
            file=sys.stderr,
        )
    if novas:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False
        ) as arquivo:
            for linha in novas:
                arquivo.write(json.dumps(linha) + "\n")
        try:
            rodar(
                "bq",
                f"--project_id={projeto}",
                "load",
                "--source_format=NEWLINE_DELIMITED_JSON",
                f"{projeto}:{TABELA}",
                arquivo.name,
            )
        finally:
            Path(arquivo.name).unlink()
    print(f"{len(novas)} de {len(jogos)} jogos previstos de novo em {TABELA}")
    # Nenhuma predição com jogos na fila é falha: a API ou a gold quebrou
    return 0 if novas else 1


if __name__ == "__main__":
    sys.exit(main())
