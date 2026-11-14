#!/usr/bin/env bash
# Infra da orquestração no GCP, idempotente:
#   - a service account do Airflow (airflow-orquestrador), com os papéis que os DAGs usam;
#   - o firewall do SSH pelo IAP, por onde passam o deploy e o túnel da interface;
#   - com ALERTA_EMAIL no .env, o canal de e-mail e a política de alerta sobre o log
#     foota-toota-alertas. Sem ALERTA_EMAIL, as falhas ficam no Cloud Logging e na interface;
#   - com AVISO_EMAILS (ou só ALERTA_EMAIL), a política que avisa o time por e-mail quando o
#     batch_diario publica dados novos e a plataforma já os carregou (log foota-toota-avisos).
#
#   orquestracao/infra.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$root/.env"
    set +a
fi

: "${GCP_PROJECT_ID:?set GCP_PROJECT_ID in .env}"
GCLOUD="${GCLOUD_BIN:-gcloud}"
REGIAO=us-central1
SA_NOME=airflow-orquestrador
SA="$SA_NOME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
project="--project=$GCP_PROJECT_ID"

echo "=== APIs"
"$GCLOUD" services enable compute.googleapis.com iap.googleapis.com monitoring.googleapis.com \
    logging.googleapis.com run.googleapis.com dataflow.googleapis.com "$project"

echo "=== service account $SA"
if ! "$GCLOUD" iam service-accounts describe "$SA" "$project" >/dev/null 2>&1; then
    "$GCLOUD" iam service-accounts create "$SA_NOME" --display-name="Airflow do foota-toota" "$project"
fi
# run.developer: executar os Jobs com outros argumentos e mudar o min-instances da API;
# dataflow.admin: lançar o Flex Template e drenar o job; BigQuery: ler o split e o atraso
for papel in roles/run.developer roles/dataflow.admin roles/bigquery.jobUser \
    roles/bigquery.dataViewer roles/logging.logWriter roles/monitoring.metricWriter; do
    "$GCLOUD" projects add-iam-policy-binding "$GCP_PROJECT_ID" --member="serviceAccount:$SA" \
        --role="$papel" --condition=None >/dev/null
done
numero="$("$GCLOUD" projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
# agir como a conta da API (nova revisão) e a dos workers do Dataflow (lançar o template)
for conta in "modelo-api@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
    "$numero-compute@developer.gserviceaccount.com"; do
    "$GCLOUD" iam service-accounts add-iam-policy-binding "$conta" --member="serviceAccount:$SA" \
        --role=roles/iam.serviceAccountUser "$project" >/dev/null
done
"$GCLOUD" run services add-iam-policy-binding modelo-api --region="$REGIAO" \
    --member="serviceAccount:$SA" --role=roles/run.invoker "$project" >/dev/null
"$GCLOUD" storage buckets add-iam-policy-binding "gs://foota-toota-505511-stream" \
    --member="serviceAccount:$SA" --role=roles/storage.objectViewer "$project" >/dev/null

echo "=== firewall: SSH só pelo IAP para a tag airflow"
if ! "$GCLOUD" compute firewall-rules describe foota-toota-iap-ssh "$project" >/dev/null 2>&1; then
    "$GCLOUD" compute firewall-rules create foota-toota-iap-ssh --network=default \
        --direction=INGRESS --allow=tcp:22 --source-ranges=35.235.240.0/20 \
        --target-tags=airflow "$project"
fi

# canal_email <e-mail>: o canal de e-mail do Cloud Monitoring para o endereço, criado se faltar
canal_email() {
    local nome="foota-toota $1" canal
    canal="$("$GCLOUD" beta monitoring channels list "$project" \
        --filter="labels.email_address=\"$1\"" --format='value(name)' | head -1)"
    if [ -z "$canal" ]; then
        canal="$("$GCLOUD" beta monitoring channels create "$project" --display-name="$nome" \
            --type=email --channel-labels="email_address=$1" --format='value(name)')"
    fi
    echo "$canal"
}

# politica <arquivo.json> <nome> <canais em JSON>: cria ou atualiza a política de alerta
politica() {
    local json nome="$2" existente
    json="$(mktemp)"
    sed -e "s|PROJECT|$GCP_PROJECT_ID|g" -e "s|CANAIS|$3|g" \
        "$root/orquestracao/$1" > "$json"
    existente="$("$GCLOUD" monitoring policies list "$project" \
        --filter="displayName=\"$nome\"" --format='value(name)' | head -1)"
    if [ -z "$existente" ]; then
        "$GCLOUD" monitoring policies create --policy-from-file="$json" "$project" >/dev/null
    else
        "$GCLOUD" monitoring policies update "$existente" --policy-from-file="$json" "$project" >/dev/null
    fi
    rm -f "$json"
}

echo "=== alerta de falha por e-mail (time de dados)"
if [ -n "${ALERTA_EMAIL:-}" ]; then
    canal="$(canal_email "$ALERTA_EMAIL")"
    politica alerta.json "foota-toota: falha no Airflow" "[\"$canal\"]"
    echo "falhas para $ALERTA_EMAIL"
else
    echo "aviso: ALERTA_EMAIL ausente no .env; sem e-mail (as falhas ficam no log foota-toota-alertas)" >&2
fi

echo "=== aviso de dados atualizados por e-mail (o time todo)"
# AVISO_EMAILS: endereços separados por vírgula; sem ele, o aviso vai para o ALERTA_EMAIL
destinos="${AVISO_EMAILS:-${ALERTA_EMAIL:-}}"
if [ -n "$destinos" ]; then
    canais=()
    IFS=',' read -r -a enderecos <<< "$destinos"
    for email in "${enderecos[@]}"; do
        email="$(echo "$email" | tr -d '[:space:]')"
        [ -n "$email" ] && canais+=("\"$(canal_email "$email")\"")
    done
    lista="$(IFS=,; echo "${canais[*]}")"
    politica aviso.json "foota-toota: dados atualizados" "[$lista]"
    echo "aviso para ${#canais[@]} endereço(s)"
else
    echo "aviso: sem AVISO_EMAILS nem ALERTA_EMAIL; o aviso fica só no log foota-toota-avisos" >&2
fi
