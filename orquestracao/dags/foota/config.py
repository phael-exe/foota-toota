"""Nomes dos recursos do GCP que os DAGs acionam ou checam."""

from __future__ import annotations

import os
from datetime import timedelta


PROJETO = os.environ.get("GCP_PROJECT_ID", "pdm-bia-505511")
REGIAO = "us-central1"

JOB_COLETOR = "foota-toota-coletor"
JOB_NOTICIAS = "foota-toota-news-job"
JOB_BATCH = "foota-toota-batch"
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

CONEXAO = "google_cloud_default"
LOG_ALERTAS = "foota-toota-alertas"
# Uma execução que falhou dentro da janela vira alerta, mesmo que outra já
# tenha passado depois
JANELA_FALHAS = timedelta(minutes=30)
# Evento de jogo agendado sem predição depois disso, com o Dataflow ligado
ATRASO_MAX_MIN = 10
# A API sobe do zero em ~24 s com min-instances=0
TIMEOUT_HEALTH_S = 60

# --- publicação para a plataforma (Smart Soccer Hub) ---
# A plataforma lê o bucket público por HTTPS e relê o _manifest.json a cada
# 30 minutos, na próxima requisição; troca os dados quando a versão muda
MANIFESTO_URL = f"https://storage.googleapis.com/{BUCKET_BRONZE}/_manifest.json"
PLATAFORMA_URL = os.environ.get(
    "PLATAFORMA_URL",
    "https://soccer-hub-web-259292887756.us-central1.run.app",
)
# Os arquivos que a plataforma carrega (o fonte.py dela): um que falte derruba
# a carga inteira
TABELAS_PLATAFORMA = (
    "silver/matches",
    "silver/teams",
    "silver/standings",
    "silver/news_articles",
    "silver/match_stats",
    "silver/match_odds",
    "silver/match_goals",
    "silver/match_tactics",
    "silver/match_weather",
    "gold/match_features_brasileirao",
    "gold/match_features_epl",
    "gold/predictions",
)
LOG_AVISOS = "foota-toota-avisos"
# Exportação diária: passou disso sem exportar, o bucket parou
EXPORTACAO_MAX = timedelta(hours=36)
# A recarga da plataforma (30 min) mais a subida de uma instância nova
ESPERA_PLATAFORMA = timedelta(minutes=60)
TIMEOUT_HTTP_S = 30
