"""Alerta de falha: toda task que falha grava uma entrada ERROR no Cloud
Logging, e uma política do Cloud Monitoring sobre esse log manda o e-mail."""

from __future__ import annotations

import logging

from foota.config import LOG_ALERTAS, PROJETO


log = logging.getLogger(__name__)


def entrada_alerta(
    dag_id: str, task_id: str, run_id: str, tentativa: int, erro: str
) -> dict:
    return {
        "dag_id": dag_id,
        "task_id": task_id,
        "run_id": run_id,
        "tentativa": tentativa,
        "erro": erro,
        "mensagem": f"{dag_id}.{task_id} falhou: {erro}",
    }


def registrar_falha(context) -> None:
    """on_failure_callback dos DAGs. Nunca levanta: o alerta não pode
    esconder a falha original."""
    ti = context["ti"]
    entrada = entrada_alerta(
        ti.dag_id,
        ti.task_id,
        ti.run_id,
        ti.try_number,
        str(context.get("exception") or "sem detalhe"),
    )
    try:
        from google.cloud import logging as cloud_logging

        cliente = cloud_logging.Client(project=PROJETO)
        cliente.logger(LOG_ALERTAS).log_struct(entrada, severity="ERROR")
    except Exception:
        log.exception("não consegui gravar o alerta: %s", entrada["mensagem"])
