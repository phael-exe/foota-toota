#!/usr/bin/env bash
# Infra do CD (.github/workflows/deploy.yml) no GCP, idempotente:
#   - a conta github-deployer, só com os papéis de publicar (Cloud Build, Artifact Registry,
#     Cloud Run, Cloud Scheduler) e de agir como as contas que os serviços usam;
#   - o pool de Workload Identity Federation "github", que aceita o token OIDC do GitHub Actions
#     só deste repositório: nenhuma chave de conta de serviço sai do GCP;
#   - com o gh logado, as variáveis do repositório que o workflow lê.
# O segredo FOOTBALLDATA_API_KEY fica com quem tem a chave: gh secret set FOOTBALLDATA_API_KEY
#
#   scripts/infra_ci.sh
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
REPO="${GITHUB_REPO:-$(git -C "$root" remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')}"
SA_NOME=github-deployer
SA="$SA_NOME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
POOL=github
PROVEDOR=github-actions
project="--project=$GCP_PROJECT_ID"
numero="$("$GCLOUD" projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"

echo "=== APIs"
"$GCLOUD" services enable iamcredentials.googleapis.com sts.googleapis.com "$project"

echo "=== conta $SA"
if ! "$GCLOUD" iam service-accounts describe "$SA" "$project" >/dev/null 2>&1; then
    "$GCLOUD" iam service-accounts create "$SA_NOME" --display-name="Deploy do GitHub Actions" \
        "$project"
fi
# run.admin: revisão nova e a política de invocação da API privada; cloudbuild + storage +
# artifactregistry: gcloud builds submit e o push das imagens; cloudscheduler: os agendamentos
# de reserva; viewer: o gcloud acompanha o log do build e lê as URLs dos serviços
for papel in roles/run.admin roles/cloudbuild.builds.editor roles/storage.admin \
    roles/artifactregistry.writer roles/cloudscheduler.admin roles/viewer \
    roles/serviceusage.serviceUsageConsumer; do
    "$GCLOUD" projects add-iam-policy-binding "$GCP_PROJECT_ID" --member="serviceAccount:$SA" \
        --role="$papel" --condition=None >/dev/null
done
# agir como as contas com que os Jobs, a API e o Cloud Build rodam
for conta in "$numero-compute@developer.gserviceaccount.com" \
    "modelo-api@$GCP_PROJECT_ID.iam.gserviceaccount.com"; do
    "$GCLOUD" iam service-accounts add-iam-policy-binding "$conta" \
        --member="serviceAccount:$SA" --role=roles/iam.serviceAccountUser "$project" >/dev/null
done

echo "=== Workload Identity Federation: só $REPO"
if ! "$GCLOUD" iam workload-identity-pools describe "$POOL" --location=global "$project" \
    >/dev/null 2>&1; then
    "$GCLOUD" iam workload-identity-pools create "$POOL" --location=global \
        --display-name="GitHub Actions" "$project"
fi
if ! "$GCLOUD" iam workload-identity-pools providers describe "$PROVEDOR" \
    --workload-identity-pool="$POOL" --location=global "$project" >/dev/null 2>&1; then
    "$GCLOUD" iam workload-identity-pools providers create-oidc "$PROVEDOR" \
        --workload-identity-pool="$POOL" --location=global "$project" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
        --attribute-condition="assertion.repository == '$REPO'"
fi
membro="principalSet://iam.googleapis.com/projects/$numero/locations/global/workloadIdentityPools/$POOL/attribute.repository/$REPO"
"$GCLOUD" iam service-accounts add-iam-policy-binding "$SA" \
    --member="$membro" --role=roles/iam.workloadIdentityUser "$project" >/dev/null
provedor="projects/$numero/locations/global/workloadIdentityPools/$POOL/providers/$PROVEDOR"

echo "=== variáveis do repositório $REPO"
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh variable set GCP_WIF_PROVIDER --repo "$REPO" --body "$provedor"
    gh variable set GCP_DEPLOY_SA --repo "$REPO" --body "$SA"
    gh variable set GCP_PROJECT_ID --repo "$REPO" --body "$GCP_PROJECT_ID"
    gh variable set GCS_BUCKET --repo "$REPO" --body "$GCS_BUCKET"
else
    echo "sem gh logado; defina à mão:"
    echo "  GCP_WIF_PROVIDER=$provedor"
    echo "  GCP_DEPLOY_SA=$SA"
fi
echo "falta o segredo (uma vez): gh secret set FOOTBALLDATA_API_KEY --repo $REPO"
