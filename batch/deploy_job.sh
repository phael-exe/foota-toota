#!/usr/bin/env bash
# Publica a atualização diária do batch (scripts/atualizar_partidas.sh) como o Cloud Run Job
# foota-toota-batch: coleta as partidas, reconstrói bronze -> silver -> gold com as checagens e
# reexporta o bucket público que a plataforma lê.
#
#   batch/deploy_job.sh            # build, deploy e o agendamento de reserva
#   batch/deploy_job.sh pausar     # para o agendamento de reserva (o Airflow assume)
#   batch/deploy_job.sh retomar    # volta o agendamento de reserva (VM do Airflow parada)
#   batch/deploy_job.sh rodar      # uma execução agora
#
# Quem agenda é o DAG batch_diario (orquestracao/), que também confere que a plataforma carregou a
# versão nova e avisa o time. O Cloud Scheduler foota-toota-batch-diario é o plano B com a VM
# parada: roda o mesmo job no mesmo horário, sem a conferência nem o aviso. Com o Airflow no ar,
# pause-o, senão o job roda duas vezes.
#
# A chave do Football-Data.org vai como variável de ambiente do job, como no coletor ao vivo.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "$root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$root/.env"
    set +a
fi

: "${GCP_PROJECT_ID:?set GCP_PROJECT_ID in .env}"
: "${GCS_BUCKET:?set GCS_BUCKET in .env}"
GCLOUD="${GCLOUD_BIN:-gcloud}"
# GCP_REGION do .env é a localização do BigQuery (US), não uma região do Cloud Run
REGIAO=us-central1
JOB=foota-toota-batch
AGENDA=foota-toota-batch-diario
IMAGEM="gcr.io/$GCP_PROJECT_ID/$JOB:latest"
project="--project=$GCP_PROJECT_ID"
location="--location=$REGIAO"

case "${1:-deploy}" in
    pausar)
        "$GCLOUD" scheduler jobs pause "$AGENDA" "$location" "$project"
        exit 0
        ;;
    retomar)
        "$GCLOUD" scheduler jobs resume "$AGENDA" "$location" "$project"
        exit 0
        ;;
    rodar)
        "$GCLOUD" run jobs execute "$JOB" --region="$REGIAO" "$project"
        exit 0
        ;;
    deploy) ;;
    *)
        echo "uso: $0 [deploy|pausar|retomar|rodar]" >&2
        exit 2
        ;;
esac

: "${FOOTBALLDATA_API_KEY:?set FOOTBALLDATA_API_KEY in .env}"
if [ -n "$(git -C "$root" status --porcelain -- scripts sql batch)" ]; then
    echo "aviso: scripts/, sql/ ou batch/ com mudanças fora de commit; a imagem leva o que está no disco" >&2
fi
commit="$(git -C "$root" rev-parse --short HEAD)"

# O contexto leva só o que o job roda: o .dockerignore da raiz tira o sql/, e o Cloud Build
# usa o docker sem .dockerignore por Dockerfile
contexto="$(mktemp -d)"
trap 'rm -rf "$contexto"' EXIT
cp "$root/batch/Dockerfile" "$contexto/"
cp -r "$root/scripts" "$root/sql" "$contexto/"
rm -rf "$contexto/sql/out"
find "$contexto" -name __pycache__ -type d -prune -exec rm -rf {} +

echo "=== imagem $IMAGEM ($commit)"
"$GCLOUD" builds submit "$contexto" --tag="$IMAGEM" "$project"

echo "=== Cloud Run Job $JOB"
# A coleta espera a cota do Football-Data.org e o SQL reconstrói silver e gold: ~20 minutos.
# Sem retry no job: repetir gasta a cota de novo, e o DAG decide
"$GCLOUD" run jobs deploy "$JOB" \
    --image="$IMAGEM" \
    --region="$REGIAO" \
    --set-env-vars="GCP_PROJECT_ID=$GCP_PROJECT_ID,GCS_BUCKET=$GCS_BUCKET,FOOTBALLDATA_API_KEY=$FOOTBALLDATA_API_KEY,COMMIT=$commit" \
    --memory=2Gi \
    --cpu=1 \
    --max-retries=0 \
    --task-timeout=3600s \
    "$project"

echo "=== agendamento de reserva $AGENDA (09:00 UTC, como o DAG batch_diario)"
numero="$("$GCLOUD" projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
conta="$numero-compute@developer.gserviceaccount.com"
uri="https://$REGIAO-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$GCP_PROJECT_ID/jobs/$JOB:run"
if "$GCLOUD" scheduler jobs describe "$AGENDA" "$location" "$project" >/dev/null 2>&1; then
    acao=update
else
    acao=create
fi
"$GCLOUD" scheduler jobs "$acao" http "$AGENDA" "$location" "$project" \
    --schedule="0 9 * * *" \
    --time-zone=UTC \
    --uri="$uri" \
    --http-method=POST \
    --oauth-service-account-email="$conta"

echo "com o Airflow no ar: $0 pausar"
echo "para rodar agora: $0 rodar"
