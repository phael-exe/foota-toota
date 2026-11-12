"""Coleta ao vivo a cada 5 minutos.

O Cloud Run Job `foota-toota-coletor` consulta o Football-Data.org uma vez e
publica no tópico `eventos` só as partidas que mudaram. Uma execução que
falha não é repetida: a próxima, 5 minutos depois, já é a nova tentativa.
"""

from __future__ import annotations

from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)
from airflow.sdk import dag
from foota.config import COMPETICOES_AO_VIVO, JOB_COLETOR, PROJETO, REGIAO
from foota.padrao import INICIO, PADRAO
from foota.replay import overrides


@dag(
    schedule="*/5 * * * *",
    start_date=INICIO,
    catchup=False,
    max_active_runs=1,
    default_args=PADRAO,
    tags=["coleta", "streaming"],
    doc_md=__doc__,
)
def coleta_ao_vivo():
    CloudRunExecuteJobOperator(
        task_id="coletor",
        project_id=PROJETO,
        region=REGIAO,
        job_name=JOB_COLETOR,
        overrides=overrides(
            [
                "python",
                "producer.py",
                "live",
                "--uma-vez",
                "--competicoes",
                *COMPETICOES_AO_VIVO,
            ]
        ),
        timeout_seconds=600,
        retries=0,
    )


coleta_ao_vivo()
