"""Clientes do GCP para as tasks, com as credenciais da conexão do Airflow
(na VM, a service account dela). Só os DAGs importam este módulo."""

from __future__ import annotations

from itertools import islice

from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from airflow.providers.google.common.hooks.base_google import GoogleBaseHook
from google.cloud import bigquery, dataflow_v1beta3, run_v2

from foota.config import API, CONEXAO, JOB_DATAFLOW, PROJETO, REGIAO


def credenciais():
    return GoogleBaseHook(gcp_conn_id=CONEXAO).get_credentials()


def cliente_bigquery() -> bigquery.Client:
    hook = BigQueryHook(gcp_conn_id=CONEXAO, use_legacy_sql=False)
    return hook.get_client(project_id=PROJETO)


def nome_servico_api() -> str:
    return f"projects/{PROJETO}/locations/{REGIAO}/services/{API}"


def url_api() -> str:
    cliente = run_v2.ServicesClient(credentials=credenciais())
    return cliente.get_service(name=nome_servico_api()).uri


def jobs_dataflow(limite: int = 50) -> list[dataflow_v1beta3.Job]:
    """Os jobs do pipeline de streaming, ativos ou não, mais recentes antes."""
    cliente = dataflow_v1beta3.JobsV1Beta3Client(credentials=credenciais())
    pedido = dataflow_v1beta3.ListJobsRequest(
        project_id=PROJETO,
        location=REGIAO,
        filter=dataflow_v1beta3.ListJobsRequest.Filter.ALL,
    )
    jobs = islice(cliente.list_jobs(request=pedido), limite)
    return [j for j in jobs if j.name == JOB_DATAFLOW]


def job_dataflow_ativo() -> dataflow_v1beta3.Job | None:
    ativos = dataflow_v1beta3.JobState
    terminais = {
        ativos.JOB_STATE_DONE,
        ativos.JOB_STATE_FAILED,
        ativos.JOB_STATE_CANCELLED,
        ativos.JOB_STATE_DRAINED,
        ativos.JOB_STATE_UPDATED,
    }
    for job in jobs_dataflow():
        if job.current_state not in terminais:
            return job
    return None
