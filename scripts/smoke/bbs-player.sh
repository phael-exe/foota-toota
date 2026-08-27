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
PLAYER_NAME="${PLAYER_NAME:-Kylian Mbappe}"

echo "Buscando jogador: ${PLAYER_NAME}"

search_response="$(
    curl --get \
        --fail-with-body \
        --silent \
        --show-error \
        "${API_URL}/v1/players" \
        --data-urlencode "name=${PLAYER_NAME}" \
        --data-urlencode "sport=${SPORT}" \
        --data-urlencode "limit=10" \
        --header "Authorization: Bearer ${BIGBALLSDATA_API_KEY}"
)"

if ! player_json="$(jq -cer '.data[0] // empty' <<<"${search_response}")"; then
    echo "Erro: nenhum jogador encontrado para '${PLAYER_NAME}'." >&2
    jq . <<<"${search_response}" >&2
    exit 1
fi

matched_player_name="$(
    jq -r '.name // .display_name // .full_name // "nome indisponível"' \
        <<<"${player_json}"
)"

echo "Jogador encontrado: ${matched_player_name}"
jq . <<<"${player_json}"
