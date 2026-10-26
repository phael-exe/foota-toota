#!/usr/bin/env bash
# Cria a infraestrutura de streaming no GCP. Pode rodar de novo: o que já existe
# fica como está.
#
#   streaming/infra.sh
#
#   API do Dataflow e bucket privado gs://$STREAM_BUCKET (estado do coletor, temporários do Dataflow)
#   dataset stream, tabelas e views (sql/10_stream)
#   tópicos eventos, predicoes e predicoes-dlq
#   assinaturas:
#     eventos-dataflow      pull, lida pelo pipeline (streaming/pipeline.py)
#     eventos-bigquery      grava cada evento bruto em stream.eventos_brutos, sem código
#     predicoes-bigquery    grava cada predição em stream.predicoes; após 5 falhas vai para predicoes-dlq
#     predicoes-dlq-sub     pull, para ver as predições que o BigQuery recusou
#     eventos-api           push para a API do modelo, se EVENTOS_PUSH_URL estiver definido
#     predicoes-plataforma  push para a plataforma, se PREDICOES_PUSH_URL estiver definido
#   conta de serviço pubsub-push, que assina o token OIDC dos pushes
#
# Permissões para as contas de serviço do time, se definidas:
#   MODELO_SA      publica no tópico predicoes
#   PLATAFORMA_SA  lê stream, gold e silver (as views da gold leem a silver) e roda consultas
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
PUSH_SA="pubsub-push@$GCP_PROJECT_ID.iam.gserviceaccount.com"
GCLOUD="${GCLOUD_BIN:-gcloud}"
BQ="${BQ_BIN:-bq}"
project="--project=$GCP_PROJECT_ID"

existe() { "$@" >/dev/null 2>&1; }

assinatura() {
    local nome="$1"
    shift
    if existe "$GCLOUD" pubsub subscriptions describe "$nome" "$project"; then
        echo "  $nome já existe"
    else
        "$GCLOUD" pubsub subscriptions create "$nome" "$@" "$project"
    fi
}

echo "=== API do Dataflow"
"$GCLOUD" services enable dataflow.googleapis.com "$project"

echo "=== bucket privado gs://$STREAM_BUCKET"
if ! existe "$GCLOUD" storage buckets describe "gs://$STREAM_BUCKET" "$project"; then
    "$GCLOUD" storage buckets create "gs://$STREAM_BUCKET" --location="$STREAM_REGION" \
        --uniform-bucket-level-access --public-access-prevention --soft-delete-duration=0 "$project"
fi

echo "=== dataset stream, tabelas e views"
"$root/sql/run.sh" "$root/sql/10_stream"

echo "=== tópicos"
for topico in eventos predicoes predicoes-dlq; do
    existe "$GCLOUD" pubsub topics describe "$topico" "$project" \
        || "$GCLOUD" pubsub topics create "$topico" "$project"
done

echo "=== assinaturas"
assinatura eventos-dataflow --topic=eventos --ack-deadline=60 --message-retention-duration=7d
assinatura eventos-bigquery --topic=eventos \
    --bigquery-table="$GCP_PROJECT_ID:stream.eventos_brutos" --write-metadata
assinatura predicoes-dlq-sub --topic=predicoes-dlq --message-retention-duration=7d
assinatura predicoes-bigquery --topic=predicoes \
    --bigquery-table="$GCP_PROJECT_ID:stream.predicoes" --use-table-schema --drop-unknown-fields \
    --dead-letter-topic=predicoes-dlq --max-delivery-attempts=5

# Para desviar para a DLQ, o agente do Pub/Sub precisa publicar nela e consumir a assinatura de origem
numero="$("$GCLOUD" projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
agente="serviceAccount:service-$numero@gcp-sa-pubsub.iam.gserviceaccount.com"
"$GCLOUD" pubsub topics add-iam-policy-binding predicoes-dlq \
    --member="$agente" --role=roles/pubsub.publisher "$project" >/dev/null
"$GCLOUD" pubsub subscriptions add-iam-policy-binding predicoes-bigquery \
    --member="$agente" --role=roles/pubsub.subscriber "$project" >/dev/null

# Os pushes levam um token OIDC desta conta (audience = URL do endpoint), para o modelo e a
# plataforma conferirem que a chamada veio do nosso Pub/Sub
echo "=== conta de serviço do push: $PUSH_SA"
if ! existe "$GCLOUD" iam service-accounts describe "$PUSH_SA" "$project"; then
    "$GCLOUD" iam service-accounts create "${PUSH_SA%%@*}" \
        --display-name="Push do Pub/Sub para o modelo e a plataforma" "$project"
fi
"$GCLOUD" iam service-accounts add-iam-policy-binding "$PUSH_SA" \
    --member="$agente" --role=roles/iam.serviceAccountTokenCreator "$project" >/dev/null

if [ -n "${EVENTOS_PUSH_URL:-}" ]; then
    assinatura eventos-api --topic=eventos --push-endpoint="$EVENTOS_PUSH_URL" --ack-deadline=60 \
        --push-auth-service-account="$PUSH_SA"
fi
if [ -n "${PREDICOES_PUSH_URL:-}" ]; then
    assinatura predicoes-plataforma --topic=predicoes --push-endpoint="$PREDICOES_PUSH_URL" \
        --push-auth-service-account="$PUSH_SA"
fi

if [ -n "${MODELO_SA:-}" ]; then
    echo "=== $MODELO_SA publica em predicoes"
    "$GCLOUD" pubsub topics add-iam-policy-binding predicoes \
        --member="serviceAccount:$MODELO_SA" --role=roles/pubsub.publisher "$project" >/dev/null
fi
if [ -n "${PLATAFORMA_SA:-}" ]; then
    echo "=== $PLATAFORMA_SA lê stream, gold e silver"
    "$GCLOUD" projects add-iam-policy-binding "$GCP_PROJECT_ID" \
        --member="serviceAccount:$PLATAFORMA_SA" --role=roles/bigquery.jobUser >/dev/null
    for dataset in stream gold silver; do
        "$BQ" --project_id="$GCP_PROJECT_ID" add-iam-policy-binding \
            --member="serviceAccount:$PLATAFORMA_SA" --role=roles/bigquery.dataViewer \
            "$GCP_PROJECT_ID:$dataset" >/dev/null
    done
fi

echo "pronto"
