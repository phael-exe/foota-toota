"""Atualização diária do batch e publicação para a plataforma, às 09:00 UTC
(06:00 em Brasília: os jogos da noite já acabaram e as notícias das 06:00 UTC
já estão no bucket).

1. `versao_anterior`: a versão do `_manifest.json` público antes de rodar;
2. `atualizar`: o Cloud Run Job `foota-toota-batch`
   (scripts/atualizar_partidas.sh): coleta o Football-Data.org e o
   Football-Data.co.uk, reconstrói bronze, silver e gold com as checagens de
   qualidade e reexporta o bucket público, com o manifesto por último. Uma
   checagem que falha para o job antes da exportação, e o bucket fica na
   versão anterior;
3. `versao_nova`: o manifesto mudou de versão, senão a exportação não aconteceu;
4. `plataforma_carregou`: espera o `/api/futebol/versao` da plataforma mostrar
   a versão nova. Ela relê o manifesto a cada 30 minutos, na próxima requisição,
   e a consulta deste sensor é essa requisição;
5. `avisar_time`: grava o aviso no log `foota-toota-avisos`, e a política
   "foota-toota: dados atualizados" manda o e-mail para AVISO_EMAILS.

Qualquer falha vira alerta para o time de dados, como nos outros DAGs.
"""

from __future__ import annotations

from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)
from airflow.sdk import PokeReturnValue, dag, task
from airflow.sdk.exceptions import AirflowFailException
from foota.config import (
    ESPERA_PLATAFORMA,
    JOB_BATCH,
    LOG_AVISOS,
    PLATAFORMA_URL,
    PROJETO,
    REGIAO,
    TIMEOUT_HTTP_S,
)
from foota.padrao import INICIO, PADRAO
from foota.publicacao import ler_manifesto


@dag(
    schedule="0 9 * * *",
    start_date=INICIO,
    catchup=False,
    max_active_runs=1,
    default_args=PADRAO,
    tags=["batch", "plataforma"],
    doc_md=__doc__,
)
def batch_diario():
    @task
    def versao_anterior() -> dict:
        from foota.publicacao import versao_do_manifesto

        manifesto = ler_manifesto()
        versao_do_manifesto(manifesto)
        return manifesto

    atualizar = CloudRunExecuteJobOperator(
        task_id="atualizar",
        project_id=PROJETO,
        region=REGIAO,
        job_name=JOB_BATCH,
        timeout_seconds=3600,
        # a coleta gasta a cota do Football-Data.org: repetir é decisão de gente
        retries=0,
    )

    @task
    def versao_nova(anterior: dict) -> dict:
        from foota.publicacao import versao_do_manifesto

        novo = ler_manifesto()
        if versao_do_manifesto(novo) == versao_do_manifesto(anterior):
            raise AirflowFailException(
                f"o job terminou, mas o manifesto continua na versão "
                f"{anterior['version']}: a exportação não aconteceu"
            )
        return novo

    @task.sensor(
        poke_interval=120,
        timeout=ESPERA_PLATAFORMA.total_seconds(),
        mode="reschedule",
    )
    def plataforma_carregou(novo: dict) -> PokeReturnValue:
        import requests
        from foota.publicacao import versao_da_plataforma

        try:
            resposta = requests.get(
                f"{PLATAFORMA_URL}/api/futebol/versao", timeout=TIMEOUT_HTTP_S
            )
            corpo = resposta.json() if resposta.ok else None
        except (requests.RequestException, ValueError):
            corpo = None
        no_ar = versao_da_plataforma(corpo)
        pronta = no_ar == novo["version"]
        return PokeReturnValue(is_done=pronta, xcom_value=no_ar)

    @task
    def avisar_time(anterior: dict, novo: dict) -> str:
        from foota.publicacao import resumo_aviso
        from google.cloud import logging as cloud_logging

        mensagem = resumo_aviso(anterior, novo, PLATAFORMA_URL)
        cliente = cloud_logging.Client(project=PROJETO)
        cliente.logger(LOG_AVISOS).log_struct(
            {"mensagem": mensagem, "versao": novo["version"]},
            severity="NOTICE",
        )
        return mensagem

    anterior = versao_anterior()
    novo = versao_nova(anterior)
    anterior >> atualizar >> novo
    plataforma_carregou(novo) >> avisar_time(anterior, novo)


batch_diario()
