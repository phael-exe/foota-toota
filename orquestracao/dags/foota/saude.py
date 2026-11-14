"""Julgamento da saúde do pipeline. Cada função recebe o que o DAG leu do GCP
e devolve a mensagem do problema, ou nada quando está tudo bem."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from foota.config import PROJETO


SQL = Path(__file__).resolve().parent / "sql"


def problema_api(status: int, corpo: dict | None) -> str | None:
    """Liga sem campeão não é problema: a API responde sem_campeao de
    propósito, e o Dataflow grava o motivo."""
    if status != 200:
        return f"/health respondeu {status}"
    if not (corpo or {}).get("ligas"):
        return "a API não carregou nenhuma liga"
    return None


def falhas_de_execucao(
    execucoes: list[dict], agora: datetime, janela: timedelta
) -> list[str]:
    return [
        f"{e['job']}: execução {e['nome']} falhou às {e['fim']:%H:%M} UTC"
        for e in execucoes
        if e["falhou"] and e["fim"] is not None and e["fim"] >= agora - janela
    ]


def estado_dataflow(
    jobs: list[dict], agora: datetime, janela: timedelta
) -> tuple[datetime | None, str | None]:
    """(início do job rodando, problema). Drenado ou cancelado é o estado
    normal fora das janelas de jogo: os eventos esperam na assinatura."""
    if not jobs:
        return None, None
    ultimo = max(jobs, key=lambda j: j["inicio"])
    if ultimo["estado"] == "JOB_STATE_RUNNING":
        return ultimo["inicio"], None
    fim = ultimo["fim"]
    if (
        ultimo["estado"] == "JOB_STATE_FAILED"
        and fim is not None
        and fim >= agora - janela
    ):
        return None, f"o job do Dataflow falhou às {fim:%H:%M} UTC"
    return None, None


def problema_atraso(
    pendentes: int, mais_antigo: datetime | None, limite_min: int
) -> str | None:
    if pendentes <= 0:
        return None
    hora = f"{mais_antigo:%H:%M} UTC" if mais_antigo else "?"
    return (
        f"{pendentes} eventos de jogo agendado sem predição há mais de "
        f"{limite_min} min (o mais antigo publicado às {hora})"
    )


def consulta_atraso() -> str:
    texto = (SQL / "eventos_sem_predicao.sql").read_text(encoding="utf-8")
    return texto.replace("PROJECT", PROJETO)
