#!/usr/bin/env bash
# Atualiza as partidas recentes no batch. Antes, prevê de novo os jogos dos próximos dias
# (scripts/repredizer.py). Depois baixa de novo o Football-Data.org (partidas e
# classificação das 10 competições), os CSVs do Football-Data.co.uk (10 ligas europeias e o
# BRA.csv), sobe essas pastas para o bronze no bucket, reconstrói as tabelas bronze dessas fontes
# e silver -> gold com as regras de qualidade, e reexporta as tabelas públicas. Partidas e
# classificação saem da mesma coleta, então a plataforma não vê rodadas diferentes.
#
#   scripts/atualizar_partidas.sh
#
# Antes de sobrescrever o bronze, a versão anterior dessas pastas vai para
# gs://$GCS_BUCKET/backup/<timestamp>/bronze/. As demais fontes (Big Balls, Transfermarkt, FPL,
# notícias) não são coletadas aqui; as notícias que o job diário (foota-toota-news-job) deixou no
# bucket entram no bronze do BigQuery antes da silver, para a plataforma não parar nelas.
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
# o Python da coleta: o do projeto (uv) na máquina, o da imagem no Cloud Run Job (PYTHON_BIN)
read -r -a python <<< "${PYTHON_BIN:-uv run python}"

echo "=== repredição dos próximos jogos, com a gold da exportação anterior"
# Antes da coleta: a API já carregou a gold da última exportação, com as odds que saíram desde
# então, e a exportação do fim leva as predições novas (gold.predicoes lê stream.predicoes_lote).
# Uma falha aqui não para a atualização dos dados, que a plataforma precisa do mesmo jeito.
if ! "${python[@]}" "$root/scripts/repredizer.py"; then
    echo "aviso: a repredição falhou; a atualização dos dados segue" >&2
fi

sources=(football_data_org football_data_org_standings football_data_uk football_data_uk_bra
         football_data_uk_fixtures football_data_uk_epl_historico)
stamp="$(date -u +%Y%m%dT%H%M%SZ)"

echo "=== backup do bronze atual em gs://$GCS_BUCKET/backup/$stamp/"
for dir in "${sources[@]}"; do
    # uma fonte nova ainda não tem pasta no bucket: não há o que guardar
    if ! "$GCLOUD" storage ls "gs://$GCS_BUCKET/bronze/$dir/" --project="$GCP_PROJECT_ID" \
        >/dev/null 2>&1; then
        continue
    fi
    "$GCLOUD" storage cp -r "gs://$GCS_BUCKET/bronze/$dir" "gs://$GCS_BUCKET/backup/$stamp/bronze/" \
        --project="$GCP_PROJECT_ID"
done

echo "=== coleta"
cd "$root"
"${python[@]}" - <<'EOF'
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
    fb.fetch_football_data_uk_fixtures(client, state)
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
    01_bronze/42_create_external_table_football_data_uk_fixtures.sql \
    01_bronze/43_create_table_football_data_uk_fixtures.sql \
    01_bronze/44_create_external_table_football_data_uk_epl_historico.sql \
    01_bronze/45_create_table_football_data_uk_epl_historico.sql \
    01_bronze/24_create_external_table_news_rss.sql \
    01_bronze/25_create_table_news_rss.sql \
    02_silver 03_silver_checks 04_gold 05_gold_checks \
    10_stream/09a_create_table_predicoes_lote.sql \
    10_stream/10_create_view_predicoes.sql \
    10_stream/12_create_view_predicoes_publicas.sql

echo "=== exportação pública"
"$root/scripts/exportar_tabelas_publicas.sh"
