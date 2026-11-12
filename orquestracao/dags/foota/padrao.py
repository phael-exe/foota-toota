"""default_args comuns a todos os DAGs: toda falha vira alerta."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from foota.alerta import registrar_falha


INICIO = datetime(2026, 11, 12, tzinfo=UTC)

PADRAO = {
    "owner": "foota-toota",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "on_failure_callback": registrar_falha,
}
