#!/usr/bin/env python3
"""Coletor do Trabalho 2: publica eventos de partida no tópico `eventos`.

Dois modos, mesmo formato de evento (contrato em docs/trabalho2/contratos.md):

  live    consulta o Football-Data.org e publica só as partidas que mudaram
          desde a consulta anterior. O último evento de cada partida fica num
          JSON no Cloud Storage, para o Cloud Run Job lembrar entre execuções.
  replay  reproduz uma temporada já coletada no bronze, rodada por rodada:
          primeiro os jogos agendados, depois os resultados. Serve para a demo,
          em que nem sempre há jogo acontecendo.

  python streaming/producer.py live --uma-vez
  python streaming/producer.py live --intervalo 300
  python streaming/producer.py replay --rodadas 28-30 --intervalo 0.5
  python streaming/producer.py replay --rodadas 30 --sem-publicar

Lê GCP_PROJECT_ID, FOOTBALLDATA_API_KEY e STREAM_BUCKET do ambiente ou do
.env na raiz do repositório.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path


API = "https://api.football-data.org/v4"
FONTE = "football_data_org"
RAIZ = Path(__file__).resolve().parent.parent
REPLAY_PADRAO = (
    "gs://foota-toota-505511/bronze/football_data_org/"
    "competition=BSA/matches.jsonl"
)

Publicar = Callable[[list[dict]], None]


def agora() -> str:
    """Instante atual em UTC, ISO 8601 com milissegundos e sufixo Z."""
    instante = datetime.now(UTC).isoformat(timespec="milliseconds")
    return instante.replace("+00:00", "Z")


def evento(
    partida: dict, mode: str, published_at: str, sufixo: str = ""
) -> dict:
    """Converte uma partida do Football-Data.org (v4) num evento do tópico.

    O event_id é determinístico: a mesma versão da partida (status, placar e
    horário) gera sempre o mesmo id, e quem consome pode descartar repetidos.
    O sufixo separa execuções de replay da mesma temporada.
    """
    placar = (partida.get("score") or {}).get("fullTime") or {}
    mandante = partida.get("homeTeam") or {}
    visitante = partida.get("awayTeam") or {}
    inicio = (partida.get("season") or {}).get("startDate") or ""
    competicao = (partida.get("competition") or {}).get("code")
    ev = {
        "event_id": None,
        "match_id": f"fdorg_{partida['id']}",
        "competition": competicao or partida.get("_competition_code"),
        "season": int(inicio[:4]) if inicio[:4].isdigit() else None,
        "matchday": partida.get("matchday"),
        "kickoff_utc": partida.get("utcDate"),
        "status": partida.get("status"),
        "home_team_id": _id(mandante),
        "home_team_name": mandante.get("name"),
        "away_team_id": _id(visitante),
        "away_team_name": visitante.get("name"),
        "score_home": placar.get("home"),
        "score_away": placar.get("away"),
        "source_id": FONTE,
        "source_updated_at": partida.get("lastUpdated"),
        "mode": mode,
        "published_at": published_at,
    }
    partes = [ev["match_id"], _versao(ev)]
    ev["event_id"] = ":".join([*partes, sufixo] if sufixo else partes)
    return ev


def _id(time_: dict) -> str | None:
    return None if time_.get("id") is None else str(time_["id"])


def _versao(ev: dict) -> str:
    gols = [
        "" if ev[c] is None else str(ev[c])
        for c in ("score_home", "score_away")
    ]
    return f"{ev['status']}:{'-'.join(gols)}:{ev['kickoff_utc']}"


# --- live -------------------------------------------------------------------


def buscar(client, chave: str, competicao: str) -> list[dict]:
    """Todas as partidas da temporada atual de uma competição."""
    url = f"{API}/competitions/{competicao}/matches"
    for _ in range(3):
        resp = client.get(url, headers={"X-Auth-Token": chave}, timeout=30.0)
        if resp.status_code == 429:
            # plano gratuito: 10 requisições por minuto
            espera = int(resp.headers.get("X-RequestCounter-Reset", "60"))
            time.sleep(espera + 1)
            continue
        resp.raise_for_status()
        partidas = resp.json().get("matches", [])
        return [{**p, "_competition_code": competicao} for p in partidas]
    raise RuntimeError(f"{competicao}: limite de requisições não liberou")


def mudancas(
    partidas: Iterable[dict], estado: dict[str, str], published_at: str
) -> list[dict]:
    """Eventos das partidas cuja versão difere da última publicada.

    Uma partida já publicada como encerrada não volta a agendada ou em
    andamento: a API às vezes responde de um cache antigo por alguns minutos
    e devolve a rodada passada sem placar. Um placar corrigido passa.
    """
    novos = []
    for e in (evento(p, "live", published_at) for p in partidas):
        anterior = estado.get(e["match_id"])
        if anterior == e["event_id"]:
            continue
        encerrada = anterior is not None and ":FINISHED:" in anterior
        if encerrada and e["status"] != "FINISHED":
            continue
        novos.append(e)
    return novos


def live(args, publicar: Publicar) -> None:
    import httpx

    chave = os.environ.get("FOOTBALLDATA_API_KEY")
    if not chave:
        sys.exit("FOOTBALLDATA_API_KEY ausente")
    with httpx.Client(headers={"User-Agent": "FootaToota/0.1"}) as client:
        while True:
            estado = json.loads(_ler(args.estado) or "{}")
            for competicao in args.competicoes:
                novos = mudancas(
                    buscar(client, chave, competicao), estado, agora()
                )
                publicar(novos)
                estado.update({e["match_id"]: e["event_id"] for e in novos})
                _log(f"{competicao}: {len(novos)} eventos publicados")
            _gravar(args.estado, json.dumps(estado, sort_keys=True))
            if args.uma_vez:
                return
            time.sleep(args.intervalo)


# --- replay -----------------------------------------------------------------


def linha_do_tempo(
    partidas: Iterable[dict],
    temporada: int | None = None,
    rodadas: set[int] | None = None,
) -> list[dict]:
    """A temporada como aconteceu: em cada rodada, os agendados e depois os
    resultados. Só entram partidas já encerradas, para o resultado ser real.
    Sem temporada, usa a mais recente do arquivo."""
    encerradas = [p for p in partidas if p.get("status") == "FINISHED"]
    if temporada is None:
        temporada = max((_temporada(p) or 0 for p in encerradas), default=0)
    por_rodada: dict[int, list[dict]] = defaultdict(list)
    for p in encerradas:
        rodada = p.get("matchday")
        if _temporada(p) == temporada and (
            rodadas is None or rodada in rodadas
        ):
            por_rodada[rodada].append(p)
    saida: list[dict] = []
    for rodada in sorted(por_rodada):
        jogos = sorted(por_rodada[rodada], key=lambda p: p["utcDate"])
        saida += [_agendada(p) for p in jogos]
        saida += jogos
    return saida


def _temporada(partida: dict) -> int | None:
    inicio = (partida.get("season") or {}).get("startDate") or ""
    return int(inicio[:4]) if inicio[:4].isdigit() else None


def _agendada(partida: dict) -> dict:
    p = copy.deepcopy(partida)
    p["status"] = "TIMED"
    p["score"] = {**(p.get("score") or {}), "winner": None}
    p["score"]["fullTime"] = {"home": None, "away": None}
    return p


def replay(args, publicar: Publicar) -> None:
    linhas = (_ler(args.arquivo) or "").splitlines()
    partidas = [json.loads(linha) for linha in linhas if linha.strip()]
    eventos = linha_do_tempo(partidas, args.temporada, args.rodadas)
    sufixo = "replay-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    _log(f"replay: {len(eventos)} eventos, 1 a cada {args.intervalo}s")
    for i, partida in enumerate(eventos, 1):
        ev = evento(partida, "replay", agora(), sufixo)
        publicar([ev])
        placar = f"{ev['score_home']}-{ev['score_away']}"
        _log(
            f"[{i}/{len(eventos)}] rodada {ev['matchday']} {ev['status']:<8} "
            f"{ev['home_team_name']} {placar} {ev['away_team_name']}"
        )
        time.sleep(args.intervalo)


# --- E/S --------------------------------------------------------------------


def publicador(projeto: str, topico: str) -> Publicar:
    from google.cloud import pubsub_v1

    cliente = pubsub_v1.PublisherClient()
    caminho = cliente.topic_path(projeto, topico)

    def publicar(eventos: list[dict]) -> None:
        futuros = [
            cliente.publish(
                caminho,
                json.dumps(e, ensure_ascii=False).encode(),
                mode=e["mode"],
                competition=e["competition"] or "",
            )
            for e in eventos
        ]
        for futuro in futuros:
            futuro.result(timeout=60)

    return publicar


def imprimir(eventos: list[dict]) -> None:
    for e in eventos:
        print(json.dumps(e, ensure_ascii=False), flush=True)


def _ler(caminho: str) -> str | None:
    if caminho.startswith("gs://"):
        blob = _blob(caminho)
        return blob.download_as_text() if blob.exists() else None
    arquivo = Path(caminho)
    return arquivo.read_text(encoding="utf-8") if arquivo.exists() else None


def _gravar(caminho: str, texto: str) -> None:
    if caminho.startswith("gs://"):
        _blob(caminho).upload_from_string(
            texto, content_type="application/json"
        )
        return
    arquivo = Path(caminho)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(texto, encoding="utf-8")


def _blob(caminho: str):
    from google.cloud import storage

    bucket, nome = caminho.removeprefix("gs://").split("/", 1)
    cliente = storage.Client(project=os.environ.get("GCP_PROJECT_ID"))
    return cliente.bucket(bucket).blob(nome)


def _log(mensagem: str) -> None:
    print(mensagem, file=sys.stderr, flush=True)


def _carregar_env() -> None:
    """Completa o ambiente com o .env da raiz, sem sobrescrever o que já há."""
    env = RAIZ / ".env"
    if not env.exists():
        return
    for linha in env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip("'\""))


def _rodadas(texto: str) -> set[int]:
    """'28-30' -> {28, 29, 30}; '5,7' -> {5, 7}."""
    rodadas: set[int] = set()
    for parte in texto.split(","):
        inicio, _, fim = parte.partition("-")
        rodadas.update(range(int(inicio), int(fim or inicio) + 1))
    return rodadas


def main(argv: list[str] | None = None) -> None:
    _carregar_env()
    bucket = os.environ.get("STREAM_BUCKET", "foota-toota-505511-stream")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--topico", default="eventos")
    parser.add_argument(
        "--sem-publicar",
        action="store_true",
        help="imprime os eventos em vez de publicar no Pub/Sub",
    )
    modos = parser.add_subparsers(dest="modo", required=True)

    p_live = modos.add_parser("live", help="consulta a API e publica mudanças")
    p_live.add_argument("--competicoes", nargs="+", default=["BSA"])
    p_live.add_argument("--uma-vez", action="store_true")
    p_live.add_argument("--intervalo", type=float, default=300.0)
    p_live.add_argument(
        "--estado", default=f"gs://{bucket}/coletor/estado.json"
    )

    p_replay = modos.add_parser("replay", help="reproduz uma temporada")
    p_replay.add_argument("--arquivo", default=REPLAY_PADRAO)
    p_replay.add_argument("--temporada", type=int)
    p_replay.add_argument("--rodadas", type=_rodadas)
    p_replay.add_argument("--intervalo", type=float, default=1.0)

    args = parser.parse_args(argv)
    if args.sem_publicar:
        publicar = imprimir
    else:
        projeto = os.environ.get("GCP_PROJECT_ID")
        if not projeto:
            sys.exit("GCP_PROJECT_ID ausente")
        # as bibliotecas do Google cobram cota do projeto do ADC local
        os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", projeto)
        publicar = publicador(projeto, args.topico)
    (live if args.modo == "live" else replay)(args, publicar)


if __name__ == "__main__":
    main()
