#!/usr/bin/env bash
# Publica a API do modelo (modelo/api.py) como serviço Cloud Run no projeto dos modelos. Pode rodar
# de novo: o que já existe fica como está e o serviço ganha uma revisão nova.
#
#   modelo/deploy_api.sh
#
#   APIs do Cloud Run, Cloud Build, Artifact Registry e Vertex AI
#   conta de serviço modelo-api: lê o Model Registry e os artefatos no Cloud Storage
#   tabela modelo.predicoes_vs_real (modelo/sql/), que a conta grava com MERGE
#   repositório de imagens foota-toota em $MODELO_REGIAO
#   serviço modelo-api, com PUSH_AUDIENCE = a URL do próprio /pubsub
#
# No fim imprime o que mandar para o Raphael (seção 6 do contrato). Com MODELO_PUBLICO=0 o
# serviço exige autenticação: o Cloud Run valida o token do push e o /predict precisa de
# `Authorization: Bearer $(gcloud auth print-identity-token)`.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "$root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$root/.env"
    set +a
fi

MODELO_PROJECT_ID="${MODELO_PROJECT_ID:-${GCP_PROJECT_ID:-}}"
: "${MODELO_PROJECT_ID:?set MODELO_PROJECT_ID (ou GCP_PROJECT_ID) in .env}"
MODELO_REGIAO="${MODELO_REGIAO:-us-central1}"
MODELO_PUBLICO="${MODELO_PUBLICO:-1}"
PIPELINE_PROJECT_ID="${PIPELINE_PROJECT_ID:-pdm-bia-505511}"
GCLOUD="${GCLOUD_BIN:-gcloud}"
BQ="${BQ_BIN:-bq}"
SERVICO="modelo-api"
TABELA="$MODELO_PROJECT_ID.modelo.predicoes_vs_real"
SA="$SERVICO@$MODELO_PROJECT_ID.iam.gserviceaccount.com"
PUSH_SA="pubsub-push@$PIPELINE_PROJECT_ID.iam.gserviceaccount.com"
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
for papel in roles/aiplatform.viewer roles/storage.objectViewer roles/bigquery.jobUser; do
    "$GCLOUD" projects add-iam-policy-binding "$MODELO_PROJECT_ID" \
        --member="serviceAccount:$SA" --role="$papel" --condition=None >/dev/null
done

echo "=== tabela $TABELA"
sed "s/\`PROJECT\./\`$MODELO_PROJECT_ID./g" "$root/modelo/sql/predicoes_vs_real.sql" \
    | "$BQ" query --use_legacy_sql=false --project_id="$MODELO_PROJECT_ID" >/dev/null
# GRANT em SQL: o `bq add-iam-policy-binding` em dataset pede allowlist do projeto
echo "GRANT \`roles/bigquery.dataEditor\` ON SCHEMA \`$MODELO_PROJECT_ID.modelo\`
      TO \"serviceAccount:$SA\"" \
    | "$BQ" query --use_legacy_sql=false --project_id="$MODELO_PROJECT_ID" >/dev/null

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
    verificar=1
else
    acesso="--no-allow-unauthenticated"
    verificar=0
fi

echo "=== Cloud Run $SERVICO"
"$GCLOUD" run deploy "$SERVICO" \
    --image="$IMAGEM" \
    "$region" \
    --service-account="$SA" \
    "$acesso" \
    --set-env-vars="MODELO_PROJECT_ID=$MODELO_PROJECT_ID,MODELO_REGIAO=$MODELO_REGIAO,TOPICO_PREDICOES=projects/$PIPELINE_PROJECT_ID/topics/predicoes,PUSH_SA=$PUSH_SA,VERIFICAR_TOKEN=$verificar,TABELA_AVALIACAO=$TABELA" \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --timeout=60s \
    "$project"

url="$("$GCLOUD" run services describe "$SERVICO" "$region" "$project" \
    --format='value(status.url)')"

# O token do push leva audience = a URL exata cadastrada na assinatura
echo "=== PUSH_AUDIENCE=$url/pubsub"
"$GCLOUD" run services update "$SERVICO" "$region" "$project" \
    --update-env-vars="PUSH_AUDIENCE=$url/pubsub"

if [ "$MODELO_PUBLICO" != "1" ]; then
    echo "=== $PUSH_SA pode chamar o serviço"
    "$GCLOUD" run services add-iam-policy-binding "$SERVICO" "$region" "$project" \
        --member="serviceAccount:$PUSH_SA" --role=roles/run.invoker >/dev/null
fi

cat <<EOF

pronto: $url  (confira em $url/health)

Mande para o Raphael:
  URL do /pubsub:   $url/pubsub
  conta de serviço: $SA

Ele roda:
  EVENTOS_PUSH_URL=$url/pubsub MODELO_SA=$SA streaming/infra.sh
EOF
