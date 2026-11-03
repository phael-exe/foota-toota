#!/usr/bin/env bash
# Atualiza as partidas recentes no batch: baixa de novo o Football-Data.org (partidas e
# classificação das 10 competições), os CSVs do Football-Data.co.uk (10 ligas europeias e o
# BRA.csv), sobe essas pastas para o bronze no bucket, reconstrói as tabelas bronze dessas fontes
# e silver -> gold com as regras de qualidade, e reexporta as tabelas públicas. Partidas e
# classificação saem da mesma coleta, então a plataforma não vê rodadas diferentes.
#
#   scripts/atualizar_partidas.sh
#
# Antes de sobrescrever o bronze, a versão anterior dessas pastas vai para
# gs://$GCS_BUCKET/backup/<timestamp>/bronze/. As demais fontes (Big Balls, Transfermarkt, FPL,
# notícias) não são tocadas.
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

sources=(football_data_org football_data_org_standings football_data_uk football_data_uk_bra)
stamp="$(date -u +%Y%m%dT%H%M%SZ)"

echo "=== backup do bronze atual em gs://$GCS_BUCKET/backup/$stamp/"
for dir in "${sources[@]}"; do
    "$GCLOUD" storage cp -r "gs://$GCS_BUCKET/bronze/$dir" "gs://$GCS_BUCKET/backup/$stamp/bronze/" \
        --project="$GCP_PROJECT_ID"
done

echo "=== coleta"
cd "$root"
uv run python - <<'EOF'
import sys
import time

sys.path.insert(0, "scripts")
import httpx

import fetch_bronze as fb
import fetch_transfers_and_fantasy as ftf

env = fb.load_env()
state = fb.load_checkpoint()
with httpx.Client() as client:
    fb.fetch_football_data_uk(client, state)
    fb.fetch_football_data_uk_brazil(client, state)
    fb.fetch_football_data_org(client, env.get("FOOTBALLDATA_API_KEY", ""), state)
fb.save_checkpoint(state)
# a API gratuita aceita 10 chamadas por minuto: zera a janela antes da classificação
time.sleep(61)
ftf.fetch_football_data_org_standings(env)
EOF

echo "=== upload para gs://$GCS_BUCKET/bronze/"
for dir in "${sources[@]}"; do
    "$GCLOUD" storage cp -r "data/bronze/$dir" "gs://$GCS_BUCKET/bronze/" --project="$GCP_PROJECT_ID"
done

echo "=== bronze (só as fontes coletadas) -> gold"
cd "$root/sql"
./run.sh \
    01_bronze/20_create_external_table_football_data_uk.sql \
    01_bronze/21_create_table_football_data_uk.sql \
    01_bronze/22_create_external_table_football_data_org.sql \
    01_bronze/23_create_table_football_data_org.sql \
    01_bronze/38_create_external_table_football_data_org_standings.sql \
    01_bronze/39_create_table_football_data_org_standings.sql \
    01_bronze/40_create_external_table_football_data_uk_bra.sql \
    01_bronze/41_create_table_football_data_uk_bra.sql \
    02_silver 03_silver_checks 04_gold 05_gold_checks

echo "=== exportação pública"
"$root/scripts/exportar_tabelas_publicas.sh"
