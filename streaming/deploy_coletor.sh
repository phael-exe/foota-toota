#!/usr/bin/env bash
# Publica o coletor ao vivo (streaming/producer.py live) como Cloud Run Job e agenda uma execução a
# cada 5 minutos no Cloud Scheduler. Cada execução consulta o Football-Data.org uma vez, publica no
# tópico eventos as partidas que mudaram e termina, então o custo fica no free tier.
#
#   streaming/deploy_coletor.sh            # build, deploy e agendamento
#   streaming/deploy_coletor.sh pausar     # para de coletar (o job continua lá)
#   streaming/deploy_coletor.sh retomar
#
# A chave do Football-Data.org vai como variável de ambiente do job, visível para quem tem acesso
# ao Cloud Run do projeto.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "$root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$root/.env"
    set +a
fi

: "${GCP_PROJECT_ID:?set GCP_PROJECT_ID in .env}"
: "${FOOTBALLDATA_API_KEY:?set FOOTBALLDATA_API_KEY in .env}"
STREAM_BUCKET="${STREAM_BUCKET:-foota-toota-505511-stream}"
STREAM_REGION="${STREAM_REGION:-us-central1}"
GCLOUD="${GCLOUD_BIN:-gcloud}"
JOB="foota-toota-coletor"
AGENDA="foota-toota-coletor-5min"
IMAGEM="gcr.io/$GCP_PROJECT_ID/$JOB:latest"
project="--project=$GCP_PROJECT_ID"
location="--location=$STREAM_REGION"

case "${1:-deploy}" in
    pausar)
        "$GCLOUD" scheduler jobs pause "$AGENDA" "$location" "$project"
        exit 0
        ;;
    retomar)
        "$GCLOUD" scheduler jobs resume "$AGENDA" "$location" "$project"
        exit 0
        ;;
    deploy) ;;
    *)
        echo "uso: $0 [deploy|pausar|retomar]" >&2
        exit 2
        ;;
esac

echo "=== imagem $IMAGEM"
"$GCLOUD" builds submit "$root/streaming" --tag="$IMAGEM" "$project"

echo "=== Cloud Run Job $JOB"
"$GCLOUD" run jobs deploy "$JOB" \
    --image="$IMAGEM" \
    --region="$STREAM_REGION" \
    --set-env-vars="GCP_PROJECT_ID=$GCP_PROJECT_ID,STREAM_BUCKET=$STREAM_BUCKET,FOOTBALLDATA_API_KEY=$FOOTBALLDATA_API_KEY" \
    --memory=512Mi \
    --cpu=1 \
    --max-retries=1 \
    --task-timeout=300s \
    "$project"

echo "=== agendamento $AGENDA (a cada 5 minutos)"
numero="$("$GCLOUD" projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
conta="$numero-compute@developer.gserviceaccount.com"
uri="https://$STREAM_REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$GCP_PROJECT_ID/jobs/$JOB:run"
if "$GCLOUD" scheduler jobs describe "$AGENDA" "$location" "$project" >/dev/null 2>&1; then
    acao=update
else
    acao=create
fi
"$GCLOUD" scheduler jobs "$acao" http "$AGENDA" "$location" "$project" \
    --schedule="*/5 * * * *" \
    --uri="$uri" \
    --http-method=POST \
    --oauth-service-account-email="$conta"

echo "para rodar agora: $GCLOUD run jobs execute $JOB --region=$STREAM_REGION $project"
