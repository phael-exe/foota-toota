#!/usr/bin/env bash
# Publica a API do modelo (modelo/api/) como serviço Cloud Run. Pode rodar de
# novo: o que já existe fica como está e o serviço ganha uma revisão nova.
#
#   modelo/deploy_api.sh
#
#   APIs do Cloud Run, Cloud Build, Artifact Registry e Vertex AI
#   conta de serviço modelo-api: lê o Model Registry e o bucket dos modelos
#   repositório de imagens foota-toota em $MODELO_REGIAO
#   serviço modelo-api, privado por padrão
#
# Privado (MODELO_PUBLICO=0, o padrão), quem chama precisa de roles/run.invoker
# e de `Authorization: Bearer <ID token>`. No streaming, quem chama é a conta
# dos workers do Dataflow.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "$root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$root/.env"
    set +a
fi

MODELO_PROJECT_ID="${MODELO_PROJECT_ID:-pdm-bia-505511}"
MODELO_REGIAO="${MODELO_REGIAO:-us-central1}"
MODELO_PUBLICO="${MODELO_PUBLICO:-0}"
MODELOS_BUCKET="${MODELOS_BUCKET:-$MODELO_PROJECT_ID-modelos}"
GCLOUD="${GCLOUD_BIN:-gcloud}"
SERVICO="modelo-api"
SA="$SERVICO@$MODELO_PROJECT_ID.iam.gserviceaccount.com"
REPOSITORIO="foota-toota"
IMAGEM="$MODELO_REGIAO-docker.pkg.dev/$MODELO_PROJECT_ID/$REPOSITORIO/$SERVICO:latest"
project="--project=$MODELO_PROJECT_ID"
region="--region=$MODELO_REGIAO"

existe() { "$@" >/dev/null 2>&1; }

echo "=== APIs"
"$GCLOUD" services enable run.googleapis.com cloudbuild.googleapis.com \
    artifactregistry.googleapis.com aiplatform.googleapis.com "$project"

echo "=== conta de serviço $SA"
if ! existe "$GCLOUD" iam service-accounts describe "$SA" "$project"; then
    "$GCLOUD" iam service-accounts create "$SERVICO" \
        --display-name="API do modelo (Cloud Run)" "$project"
fi
"$GCLOUD" projects add-iam-policy-binding "$MODELO_PROJECT_ID" \
    --member="serviceAccount:$SA" --role=roles/aiplatform.viewer \
    --condition=None >/dev/null
"$GCLOUD" storage buckets add-iam-policy-binding "gs://$MODELOS_BUCKET" \
    --member="serviceAccount:$SA" --role=roles/storage.objectViewer \
    "$project" >/dev/null

echo "=== repositório de imagens $REPOSITORIO"
if ! existe "$GCLOUD" artifacts repositories describe "$REPOSITORIO" \
    --location="$MODELO_REGIAO" "$project"; then
    "$GCLOUD" artifacts repositories create "$REPOSITORIO" \
        --repository-format=docker --location="$MODELO_REGIAO" "$project"
fi

echo "=== imagem $IMAGEM"
"$GCLOUD" builds submit "$root/modelo" --tag="$IMAGEM" "$project"

if [ "$MODELO_PUBLICO" = "1" ]; then
    acesso="--allow-unauthenticated"
else
    acesso="--no-allow-unauthenticated"
fi

echo "=== Cloud Run $SERVICO"
"$GCLOUD" run deploy "$SERVICO" \
    --image="$IMAGEM" \
    "$region" \
    --service-account="$SA" \
    "$acesso" \
    --set-env-vars="MODELO_PROJECT_ID=$MODELO_PROJECT_ID,MODELO_REGIAO=$MODELO_REGIAO" \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --timeout=60s \
    "$project"

url="$("$GCLOUD" run services describe "$SERVICO" "$region" "$project" \
    --format='value(status.url)')"

cat <<EOF

pronto: $url

  curl -H "Authorization: Bearer \$(gcloud auth print-identity-token)" $url/health
EOF
