#!/usr/bin/env bash
# Deploy do Foota Toota Ingestion no Google Cloud Run Jobs + Cloud Scheduler
# Executa de forma 100% serverless, sem VMs 24/7 (Custo R$ 0,00 no Free Tier).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$ROOT_DIR/.env"
    set +a
fi

GCLOUD="${GCLOUD_BIN:-gcloud}"
if [[ "$GCLOUD" == /* ]]; then
    export PATH="$(dirname "$GCLOUD"):$PATH"
fi

PROJECT_ID="${GCP_PROJECT_ID:?GCP_PROJECT_ID não definido no .env}"
BUCKET="${GCS_BUCKET:?GCS_BUCKET não definido no .env}"
REGION="${GCP_REGION:-us-central1}"
JOB_NAME="foota-toota-news-job"
IMAGE_TAG="gcr.io/${PROJECT_ID}/foota-toota-ingestion:latest"

echo "=== [1/4] Habilitando APIs necessárias no GCP ==="
gcloud services enable \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project="${PROJECT_ID}"

echo "=== [2/4] Construindo imagem Docker via Cloud Build ==="
gcloud builds submit "$ROOT_DIR" \
    --tag="${IMAGE_TAG}" \
    --project="${PROJECT_ID}"

echo "=== [3/4] Criando / Atualizando Cloud Run Job ==="
gcloud run jobs deploy "${JOB_NAME}" \
    --image="${IMAGE_TAG}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCS_BUCKET=${BUCKET},GCP_REGION=${REGION}" \
    --memory=512Mi \
    --cpu=1 \
    --max-retries=1 \
    --task-timeout=300s

echo "=== [4/4] Configurando agendamento diário no Cloud Scheduler (1x ao dia às 06:00 UTC) ==="
# Obtém a conta de serviço padrão do projeto para disparar o Job autenticado
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Garante permissão de invocador do Cloud Run para a conta de serviço
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker" >/dev/null 2>&1 || true

SCHEDULER_NAME="foota-toota-daily-run"
if gcloud scheduler jobs describe "${SCHEDULER_NAME}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "  ✓ Atualizando Cloud Scheduler existente..."
    gcloud scheduler jobs update http "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --schedule="0 6 * * *" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email="${SA_EMAIL}"
else
    echo "  ✓ Criando novo Cloud Scheduler..."
    gcloud scheduler jobs create http "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --schedule="0 6 * * *" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email="${SA_EMAIL}"
fi

echo
echo "🎉 Cloud Run Job e agendamento configurados com sucesso!"
echo "Para disparar uma execução manual de teste imediatamente:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"

