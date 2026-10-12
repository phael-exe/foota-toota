#!/usr/bin/env bash
# Exporta as tabelas silver e gold que o time usa (modelo e front) para o bucket público, para o time
# puxar sem conta no GCP:
#
#   https://storage.googleapis.com/$GCS_BUCKET/silver/<tabela>.parquet   (e .csv)
#   https://storage.googleapis.com/$GCS_BUCKET/gold/<tabela>.parquet
#
# Gold sai só em Parquet: as colunas *_history_match_ids são ARRAY, que o CSV não suporta.
# Rode de novo sempre que silver/gold forem reconstruídas; os arquivos são sobrescritos.
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
BQ="${BQ_BIN:-bq}"
GCLOUD="${GCLOUD_BIN:-gcloud}"

silver=(matches matches_brasileirao matches_epl standings match_stats match_goals match_odds
        match_tactics match_weather news_articles transfers player_valuations)
gold=(match_features_brasileirao match_features_epl)

extract() {
    local table="$1" format="$2" ext="$3"
    local uri="gs://$GCS_BUCKET/${table%%.*}/${table#*.}.$ext"
    echo "=== $table -> $uri"
    "$BQ" --project_id="$GCP_PROJECT_ID" extract --destination_format="$format" \
        "$GCP_PROJECT_ID:$table" "$uri"
}

for t in "${silver[@]}"; do
    extract "silver.$t" PARQUET parquet
    extract "silver.$t" CSV csv
done
for t in "${gold[@]}"; do
    extract "gold.$t" PARQUET parquet
done

# Sem cache no CDN público, para uma reexportação aparecer na hora
echo "=== cache-control: no-cache"
"$GCLOUD" storage objects update "gs://$GCS_BUCKET/silver/**" "gs://$GCS_BUCKET/gold/**" \
    --cache-control=no-cache --project="$GCP_PROJECT_ID"
# O bq extract grava application/octet-stream; text/csv deixa o fetch() do front tratar como texto
"$GCLOUD" storage objects update "gs://$GCS_BUCKET/silver/*.csv" \
    --content-type=text/csv --project="$GCP_PROJECT_ID"
