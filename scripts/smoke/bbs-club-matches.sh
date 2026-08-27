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
LEAGUES="${LEAGUES:-epl laliga ucl}"
LIMIT="${LIMIT:-200}"
SEASON="${SEASON:-}"

read -r -a league_ids <<<"${LEAGUES}"

if ((${#league_ids[@]} == 0)); then
    echo "Erro: informe ao menos uma competição em LEAGUES." >&2
    exit 1
fi

echo "Consultando competições disponíveis..."

leagues_response="$(
    curl --get \
        --fail-with-body \
        --silent \
        --show-error \
        --connect-timeout 10 \
        --max-time 30 \
        "${API_URL}/v1/leagues" \
        --data-urlencode "sport=${SPORT}" \
        --header "Authorization: Bearer ${BIGBALLSDATA_API_KEY}"
)"

results_file="$(mktemp)"
trap 'rm -f -- "${results_file}"' EXIT

selected_leagues="$(
    jq -c --arg ids "${LEAGUES}" '
        ($ids | split(" ") | map(select(length > 0))) as $ids
        | [.data[] | select(.id as $id | $ids | index($id)) | {id, name}]
    ' <<<"${leagues_response}"
)"

for league_id in "${league_ids[@]}"; do
    if ! league_name="$(
        jq -er --arg id "${league_id}" \
            '.data[] | select(.id == $id) | .name' \
            <<<"${leagues_response}"
    )"; then
        echo "Erro: competição '${league_id}' não encontrada em /v1/leagues." >&2
        exit 1
    fi

    echo "Buscando partidas de ${league_name} (${league_id})..."

    curl_args=(
        --get
        --fail-with-body
        --silent
        --show-error
        --connect-timeout 10
        --max-time 30
        "${API_URL}/v1/matches"
        --data-urlencode "sport=${SPORT}"
        --data-urlencode "league=${league_id}"
        --data-urlencode "limit=${LIMIT}"
        --header "Authorization: Bearer ${BIGBALLSDATA_API_KEY}"
    )

    if [[ -n "${SEASON}" ]]; then
        curl_args+=(--data-urlencode "season=${SEASON}")
    fi

    matches_response="$(curl "${curl_args[@]}")"

    jq -c \
        --arg team "${TEAM_NAME}" \
        --arg league_id "${league_id}" \
        --arg league_name "${league_name}" '
            ($team | ascii_downcase) as $needle
            | .data[]
            | select(
                ((.home.name // "" | ascii_downcase) | contains($needle))
                or ((.away.name // "" | ascii_downcase) | contains($needle))
            )
            | {
                id,
                competition: {
                    id: $league_id,
                    name: $league_name
                },
                kickoff_utc,
                status,
                home,
                away,
                score
            }
        ' <<<"${matches_response}" >>"${results_file}"
done

if [[ ! -s "${results_file}" ]]; then
    echo "Erro: nenhuma partida encontrada para '${TEAM_NAME}'." >&2
    exit 1
fi

jq -s \
    --arg team "${TEAM_NAME}" \
    --arg season "${SEASON:-auto}" \
    --argjson competitions "${selected_leagues}" '
    unique_by(.id)
    | sort_by(.kickoff_utc)
    | . as $matches
    | {
        team: $team,
        season: $season,
        total: ($matches | length),
        by_competition: (
            $competitions
            | map(
                . as $competition
                | {
                    id: $competition.id,
                    name: $competition.name,
                    total: (
                        $matches
                        | map(select(.competition.id == $competition.id))
                        | length
                    )
                }
            )
        ),
        matches: $matches
    }
' "${results_file}"
