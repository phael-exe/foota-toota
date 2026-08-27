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
TEAM_NAME="${TEAM_NAME:-Real Madrid}"
PAGE_SIZE=200

echo "Buscando clube: ${TEAM_NAME}"

offset=0
team_json=""

while [[ -z "${team_json}" ]]; do
    search_response="$(
        curl --get \
            --fail-with-body \
            --silent \
            --show-error \
            "${API_URL}/v1/teams" \
            --data-urlencode "sport=${SPORT}" \
            --data-urlencode "limit=${PAGE_SIZE}" \
            --data-urlencode "offset=${offset}" \
            --header "Authorization: Bearer ${BIGBALLSDATA_API_KEY}"
    )"

    team_json="$(
        jq -cer --arg name "${TEAM_NAME}" '
            ($name | ascii_downcase) as $needle
            | .data
            | map(select((.name | ascii_downcase) | contains($needle)))
            | first // empty
        ' <<<"${search_response}"
    )" || true

    if [[ -n "${team_json}" ]]; then
        break
    fi

    if ! total="$(jq -er '.pagination.total' <<<"${search_response}")"; then
        echo "Erro: a API retornou uma paginação inválida." >&2
        jq . <<<"${search_response}" >&2
        exit 1
    fi

    offset=$((offset + PAGE_SIZE))

    if ((offset >= total)); then
        echo "Erro: clube '${TEAM_NAME}' não encontrado para o esporte '${SPORT}'." >&2
        exit 1
    fi
done

matched_team_name="$(jq -r '.name' <<<"${team_json}")"

echo "Clube encontrado: ${matched_team_name}"
jq . <<<"${team_json}"
