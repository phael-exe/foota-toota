"""Nomes dos recursos do GCP que os DAGs acionam ou checam."""

from __future__ import annotations

import os
from datetime import timedelta


PROJETO = os.environ.get("GCP_PROJECT_ID", "pdm-bia-505511")
REGIAO = "us-central1"

JOB_COLETOR = "foota-toota-coletor"
JOB_NOTICIAS = "foota-toota-news-job"
JOB_DATAFLOW = "foota-toota-partidas"
API = "modelo-api"

BUCKET_BRONZE = "foota-toota-505511"
BUCKET_STREAM = "foota-toota-505511-stream"
TEMPLATE_DATAFLOW = f"gs://{BUCKET_STREAM}/dataflow/templates/partidas.json"
ASSINATURA_EVENTOS = f"projects/{PROJETO}/subscriptions/eventos-dataflow"

# Competições com modelo: o coletor ao vivo consulta estas, e o replay só
# aceita estas (cada uma tem a tabela com o split do treino)
COMPETICOES_AO_VIVO = ("BSA", "PL")
TABELA_SPLIT = {
    "BSA": "gold.match_training_brasileirao",
    "PL": "gold.match_training_epl",
}

LOG_ALERTAS = "foota-toota-alertas"
# Uma execução que falhou dentro da janela vira alerta, mesmo que outra já
# tenha passado depois
JANELA_FALHAS = timedelta(minutes=30)
# Evento de jogo agendado sem predição depois disso, com o Dataflow ligado
ATRASO_MAX_MIN = 10
# A API sobe do zero em ~24 s com min-instances=0
TIMEOUT_HEALTH_S = 60
