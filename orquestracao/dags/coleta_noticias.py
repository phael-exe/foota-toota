"""Coleta diária de notícias para o bronze (Cloud Run Job
`foota-toota-news-job`), às 06:00 UTC."""

from __future__ import annotations

from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)
from airflow.sdk import dag
from foota.config import JOB_NOTICIAS, PROJETO, REGIAO
from foota.padrao import INICIO, PADRAO


@dag(
    schedule="0 6 * * *",
    start_date=INICIO,
    catchup=False,
    default_args=PADRAO,
    tags=["coleta", "batch"],
    doc_md=__doc__,
)
def coleta_noticias():
    CloudRunExecuteJobOperator(
        task_id="noticias",
        project_id=PROJETO,
        region=REGIAO,
        job_name=JOB_NOTICIAS,
        timeout_seconds=900,
    )


coleta_noticias()
