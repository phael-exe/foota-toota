#!/usr/bin/env bash
# Liga e desliga o pipeline de streaming (streaming/pipeline.py) no Dataflow.
#
#   streaming/dataflow.sh iniciar
#   streaming/dataflow.sh parar     # drena: termina o que já leu e encerra
#   streaming/dataflow.sh status
#
# O job cobra por hora enquanto roda (1 worker n1-standard-1): desligue depois da demo. Desligado,
# os eventos esperam na assinatura eventos-dataflow (até 7 dias) e continuam caindo em
# stream.eventos_brutos; ao ligar de novo, o job processa o acumulado.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "$root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$root/.env"
    set +a
fi

: "${GCP_PROJECT_ID:?set GCP_PROJECT_ID in .env}"
STREAM_BUCKET="${STREAM_BUCKET:-foota-toota-505511-stream}"
STREAM_REGION="${STREAM_REGION:-us-central1}"
GCLOUD="${GCLOUD_BIN:-gcloud}"
JOB="foota-toota-partidas"
# As bibliotecas do Google cobram cota do projeto do ADC local, que pode ser outro
export GOOGLE_CLOUD_QUOTA_PROJECT="$GCP_PROJECT_ID"
venv="$root/streaming/.venv"

job_ativo() {
    "$GCLOUD" dataflow jobs list --project="$GCP_PROJECT_ID" --region="$STREAM_REGION" \
        --status=active --filter="name=$JOB" --format="value(id)"
}

case "${1:-}" in
    iniciar)
        if [ -n "$(job_ativo)" ]; then
            echo "o job $JOB já está rodando"
            exit 0
        fi
        if [ ! -x "$venv/bin/python" ]; then
            uv venv "$venv" --python 3.12 --seed
            uv pip install --python "$venv/bin/python" -r "$root/streaming/requirements-pipeline.txt"
        fi
        "$venv/bin/python" "$root/streaming/pipeline.py" \
            --runner=DataflowRunner \
            --project="$GCP_PROJECT_ID" \
            --region="$STREAM_REGION" \
            --job_name="$JOB" \
            --subscription="projects/$GCP_PROJECT_ID/subscriptions/eventos-dataflow" \
            --temp_location="gs://$STREAM_BUCKET/dataflow/temp" \
            --staging_location="gs://$STREAM_BUCKET/dataflow/staging" \
            --enable_streaming_engine \
            --num_workers=1 \
            --max_num_workers=1 \
            --machine_type=n1-standard-1 \
            --labels=projeto=foota-toota
        echo "job submetido; acompanhe em https://console.cloud.google.com/dataflow/jobs?project=$GCP_PROJECT_ID"
        ;;
    parar)
        id="$(job_ativo)"
        if [ -z "$id" ]; then
            echo "nenhum job $JOB rodando"
            exit 0
        fi
        "$GCLOUD" dataflow jobs drain "$id" --project="$GCP_PROJECT_ID" --region="$STREAM_REGION"
        ;;
    status)
        "$GCLOUD" dataflow jobs list --project="$GCP_PROJECT_ID" --region="$STREAM_REGION" \
            --filter="name=$JOB" --limit=3
        ;;
    *)
        echo "uso: $0 iniciar|parar|status" >&2
        exit 2
        ;;
esac
