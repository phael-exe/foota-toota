#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Erro: arquivo ${ENV_FILE} não encontrado" >&2
    exit 1
fi

set -a
source "${ENV_FILE}"
set +a

: "${BIGBALLSDATA_API_KEY:?Defina BIGBALLSDATA_API_KEY no arquivo .env}"

API_URL="https://api.bigballsdata.com"
SPORT="${SPORT:-football}"
LEAGUE="${LEAGUE:-epl}"
LIMIT="${LIMIT:-10}"

curl --get \
    --fail-with-body \
    --silent \
    --show-error \
    "${API_URL}/v1/matches" \
    --data-urlencode "sport=${SPORT}" \
    --data-urlencode "league=${LEAGUE}" \
    --data-urlencode "limit=${LIMIT}" \
    --header "Authorization: Bearer ${BIGBALLSDATA_API_KEY}" |
    jq .
