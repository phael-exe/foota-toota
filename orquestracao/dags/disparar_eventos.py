"""Gerador de eventos da demo: reproduz rodadas já jogadas no tópico `eventos`.

Roda o Cloud Run Job do coletor em modo replay: para cada rodada, primeiro os
jogos como agendados (o Dataflow pede a predição à API), depois os resultados.
Só aceita temporadas fora do TRAIN/EVAL do modelo em produção, para o acerto
mostrado não ser dentro da amostra.
"""

from __future__ import annotations

from airflow.providers.google.cloud.operators.cloud_run import (
    CloudRunExecuteJobOperator,
)
from airflow.sdk import Param, dag, task
from airflow.sdk.exceptions import AirflowFailException
from foota.config import JOB_COLETOR, PROJETO, REGIAO, TABELA_SPLIT
from foota.padrao import INICIO, PADRAO
from foota.replay import (
    argumentos_replay,
    checar_fora_da_amostra,
    consulta_primeira_test,
    overrides,
)


@dag(
    schedule=None,
    start_date=INICIO,
    catchup=False,
    default_args=PADRAO,
    tags=["streaming", "demo"],
    doc_md=__doc__,
    params={
        "competicao": Param("BSA", enum=list(TABELA_SPLIT)),
        "temporada": Param(2026, type="integer"),
        "rodadas": Param("31", type="string", description="31, 28-30 ou 5,7"),
        "intervalo": Param(
            0.5,
            type="number",
            minimum=0,
            maximum=10,
            description="segundos entre um evento e o próximo",
        ),
    },
)
def disparar_eventos():
    @task(retries=0)
    def checar_replay(params=None) -> dict:
        from foota.gcp import cliente_bigquery

        competicao = params["competicao"]
        temporada = int(params["temporada"])
        try:
            args = argumentos_replay(
                competicao,
                temporada,
                str(params["rodadas"]),
                float(params["intervalo"]),
            )
            consulta = cliente_bigquery().query(
                consulta_primeira_test(competicao)
            )
            primeira = next(iter(consulta.result()))["primeira"]
            checar_fora_da_amostra(competicao, temporada, primeira)
        except ValueError as erro:
            raise AirflowFailException(str(erro)) from erro
        return overrides(args)

    CloudRunExecuteJobOperator(
        task_id="replay",
        project_id=PROJETO,
        region=REGIAO,
        job_name=JOB_COLETOR,
        overrides=checar_replay(),
        timeout_seconds=1800,
        verbose=True,
        retries=0,
    )


disparar_eventos()
