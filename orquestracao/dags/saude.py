"""Saúde do pipeline a cada 15 minutos.

- `api_modelo`: o `/health` da API do modelo responde e carregou as ligas;
- `jobs_cloud_run`: nenhuma execução do coletor ou das notícias falhou nos
  últimos 30 minutos;
- `dataflow`: o último job do streaming não falhou;
- `atraso_predicao`: com o Dataflow ligado, nenhum evento de jogo agendado
  espera mais de 10 minutos pela predição. Com o Dataflow desligado, é pulada:
  os eventos esperam na assinatura de propósito.

Cada problema falha a task com a mensagem, e a falha vira alerta por e-mail.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import islice

from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowFailException, AirflowSkipException
from foota.config import (
    ATRASO_MAX_MIN,
    JANELA_FALHAS,
    JOB_COLETOR,
    JOB_NOTICIAS,
    PROJETO,
    REGIAO,
    TIMEOUT_HEALTH_S,
)
from foota.padrao import INICIO, PADRAO
from foota.saude import (
    consulta_atraso,
    estado_dataflow,
    falhas_de_execucao,
    problema_api,
    problema_atraso,
)


@dag(
    schedule="*/15 * * * *",
    start_date=INICIO,
    catchup=False,
    max_active_runs=1,
    default_args={**PADRAO, "retries": 0},
    tags=["saude"],
    doc_md=__doc__,
)
def saude():
    @task
    def api_modelo() -> dict:
        import google.auth.transport.requests
        import requests
        from foota.gcp import url_api
        from google.oauth2 import id_token

        url = url_api()
        token = id_token.fetch_id_token(
            google.auth.transport.requests.Request(), url
        )
        try:
            resposta = requests.get(
                f"{url}/health",
                headers={"Authorization": f"Bearer {token}"},
                timeout=TIMEOUT_HEALTH_S,
            )
        except requests.RequestException as erro:
            raise AirflowFailException(
                f"/health sem resposta: {erro}"
            ) from erro
        try:
            corpo = resposta.json()
        except ValueError:
            corpo = None
        problema = problema_api(resposta.status_code, corpo)
        if problema:
            raise AirflowFailException(problema)
        return {liga: d.get("versao") for liga, d in corpo["ligas"].items()}

    @task
    def jobs_cloud_run() -> int:
        from foota.gcp import credenciais
        from google.cloud import run_v2

        cliente = run_v2.ExecutionsClient(credentials=credenciais())
        execucoes = []
        for job in (JOB_COLETOR, JOB_NOTICIAS):
            pai = f"projects/{PROJETO}/locations/{REGIAO}/jobs/{job}"
            for e in islice(cliente.list_executions(parent=pai), 20):
                execucoes.append(
                    {
                        "job": job,
                        "nome": e.name.rsplit("/", 1)[-1],
                        "fim": e.completion_time,
                        "falhou": e.failed_count > 0,
                    }
                )
        falhas = falhas_de_execucao(execucoes, datetime.now(UTC), JANELA_FALHAS)
        if falhas:
            raise AirflowFailException("; ".join(falhas))
        return len(execucoes)

    @task
    def dataflow() -> str | None:
        """Devolve o início do job rodando, ou None se está desligado."""
        from foota.gcp import jobs_dataflow

        jobs = [
            {
                "estado": j.current_state.name,
                "inicio": j.create_time,
                "fim": j.current_state_time,
            }
            for j in jobs_dataflow()
        ]
        inicio, problema = estado_dataflow(
            jobs, datetime.now(UTC), JANELA_FALHAS
        )
        if problema:
            raise AirflowFailException(problema)
        return inicio.isoformat() if inicio else None

    @task
    def atraso_predicao(inicio: str | None) -> int:
        from foota.gcp import cliente_bigquery
        from google.cloud import bigquery

        if inicio is None:
            raise AirflowSkipException(
                "Dataflow desligado: os eventos esperam na assinatura"
            )
        desde = max(
            datetime.fromisoformat(inicio),
            datetime.now(UTC) - timedelta(hours=2),
        )
        config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("desde", "TIMESTAMP", desde),
                bigquery.ScalarQueryParameter(
                    "limite_min", "INT64", ATRASO_MAX_MIN
                ),
            ]
        )
        consulta = cliente_bigquery().query(
            consulta_atraso(), job_config=config
        )
        linha = next(iter(consulta.result()))
        problema = problema_atraso(
            linha["pendentes"], linha["mais_antigo"], ATRASO_MAX_MIN
        )
        if problema:
            raise AirflowFailException(problema)
        return linha["pendentes"]

    api_modelo()
    jobs_cloud_run()
    atraso_predicao(dataflow())


saude()
