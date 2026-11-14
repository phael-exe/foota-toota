"""Liga ou desliga o streaming para poupar créditos.

- `ligar`: sobe o job `foota-toota-partidas` a partir do Flex Template (se já
  não estiver rodando) e deixa a API do modelo com uma instância quente
  (min-instances=1), para a primeira predição não esperar o cold start;
- `desligar`: drena o job (termina o que já leu e encerra) e volta a API para
  min-instances=0. Desligado, os eventos esperam na assinatura por até 7 dias.
"""

from __future__ import annotations

from airflow.sdk import Param, dag, task
from foota.config import (
    ASSINATURA_EVENTOS,
    BUCKET_STREAM,
    JOB_DATAFLOW,
    PROJETO,
    REGIAO,
    TEMPLATE_DATAFLOW,
)
from foota.padrao import INICIO, PADRAO


@dag(
    schedule=None,
    start_date=INICIO,
    catchup=False,
    max_active_runs=1,
    default_args={**PADRAO, "retries": 0},
    tags=["streaming", "custo"],
    doc_md=__doc__,
    params={"acao": Param("ligar", enum=["ligar", "desligar"])},
)
def dataflow_liga_desliga():
    @task.branch
    def escolher(params=None) -> str:
        if params["acao"] == "ligar":
            return "iniciar_dataflow"
        return "drenar_dataflow"

    @task
    def iniciar_dataflow() -> str:
        from foota.gcp import credenciais, job_dataflow_ativo, url_api
        from google.cloud import dataflow_v1beta3 as df

        ativo = job_dataflow_ativo()
        if ativo is not None:
            print(f"o job {ativo.id} já está em {ativo.current_state.name}")
            return ativo.id
        ambiente = df.FlexTemplateRuntimeEnvironment(
            num_workers=1,
            max_workers=1,
            machine_type="n1-standard-1",
            enable_streaming_engine=True,
            temp_location=f"gs://{BUCKET_STREAM}/dataflow/temp",
            staging_location=f"gs://{BUCKET_STREAM}/dataflow/staging",
            additional_user_labels={"projeto": "foota-toota"},
        )
        pedido = df.LaunchFlexTemplateRequest(
            project_id=PROJETO,
            location=REGIAO,
            launch_parameter=df.LaunchFlexTemplateParameter(
                job_name=JOB_DATAFLOW,
                container_spec_gcs_path=TEMPLATE_DATAFLOW,
                parameters={
                    "api_url": url_api(),
                    "subscription": ASSINATURA_EVENTOS,
                },
                environment=ambiente,
            ),
        )
        cliente = df.FlexTemplatesServiceClient(credentials=credenciais())
        job = cliente.launch_flex_template(request=pedido).job
        print(f"job {job.id} submetido")
        return job.id

    @task
    def drenar_dataflow() -> str | None:
        from foota.gcp import credenciais, job_dataflow_ativo
        from google.cloud import dataflow_v1beta3 as df

        ativo = job_dataflow_ativo()
        if ativo is None:
            print("nenhum job ativo")
            return None
        cliente = df.JobsV1Beta3Client(credentials=credenciais())
        cliente.update_job(
            request=df.UpdateJobRequest(
                project_id=PROJETO,
                location=REGIAO,
                job_id=ativo.id,
                job=df.Job(requested_state=df.JobState.JOB_STATE_DRAINED),
            )
        )
        print(f"job {ativo.id} drenando")
        return ativo.id

    @task(trigger_rule="none_failed_min_one_success")
    def api_min_instancias(params=None) -> int:
        from foota.gcp import credenciais, nome_servico_api
        from google.cloud import run_v2
        from google.protobuf.field_mask_pb2 import FieldMask

        minimo = 1 if params["acao"] == "ligar" else 0
        cliente = run_v2.ServicesClient(credentials=credenciais())
        servico = cliente.get_service(name=nome_servico_api())
        servico.template.scaling.min_instance_count = minimo
        operacao = cliente.update_service(
            service=servico,
            update_mask=FieldMask(
                paths=["template.scaling.min_instance_count"]
            ),
        )
        operacao.result(timeout=600)
        print(f"modelo-api com min-instances={minimo}")
        return minimo

    caminho = escolher()
    ligar, desligar = iniciar_dataflow(), drenar_dataflow()
    caminho >> [ligar, desligar]
    [ligar, desligar] >> api_min_instancias()


dataflow_liga_desliga()
