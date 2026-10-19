#!/usr/bin/env bash
# Exporta as tabelas silver e gold que o time usa (modelo e front) para o bucket público, para o time
# puxar sem conta no GCP:
#
#   https://storage.googleapis.com/$GCS_BUCKET/silver/<tabela>.parquet   (e .csv)
#   https://storage.googleapis.com/$GCS_BUCKET/gold/<tabela>.parquet
#   https://storage.googleapis.com/$GCS_BUCKET/gold/predictions.parquet  (stream.predicoes, Trabalho 2)
#   https://storage.googleapis.com/$GCS_BUCKET/_manifest.json            (data, versão e linhas por arquivo)
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

silver=(teams matches matches_brasileirao matches_epl standings match_stats match_goals match_odds
        match_tactics match_weather news_articles transfers player_valuations)
gold=(match_features_brasileirao match_features_epl match_training_brasileirao match_training_epl)

exported=()

# extract <dataset.tabela> <formato> <extensão> [caminho no bucket, sem extensão]
extract() {
    local table="$1" format="$2" ext="$3" path="${4:-${1%%.*}/${1#*.}}"
    local uri="gs://$GCS_BUCKET/$path.$ext"
    echo "=== $table -> $uri"
    "$BQ" --project_id="$GCP_PROJECT_ID" extract --destination_format="$format" \
        "$GCP_PROJECT_ID:$table" "$uri"
    exported+=("$table|$path.$ext")
}

for t in "${silver[@]}"; do
    extract "silver.$t" PARQUET parquet
    extract "silver.$t" CSV csv
done
for t in "${gold[@]}"; do
    extract "gold.$t" PARQUET parquet
done
# As predições do Trabalho 2 (tópico predicoes), no formato do contrato; vazia até o modelo publicar
extract stream.predicoes PARQUET parquet gold/predictions

# Sem cache no CDN público, para uma reexportação aparecer na hora
echo "=== cache-control: no-cache"
"$GCLOUD" storage objects update "gs://$GCS_BUCKET/silver/**" "gs://$GCS_BUCKET/gold/**" \
    --cache-control=no-cache --project="$GCP_PROJECT_ID"
# O bq extract grava application/octet-stream; text/csv deixa o fetch() do front tratar como texto
"$GCLOUD" storage objects update "gs://$GCS_BUCKET/silver/*.csv" \
    --content-type=text/csv --project="$GCP_PROJECT_ID"

# Manifesto, por último: a plataforma sincroniza uma vez por dia e só baixa de novo quando a
# versão muda, então ele só aparece com todos os arquivos já no lugar
echo "=== _manifest.json"
counts="$("$BQ" --project_id="$GCP_PROJECT_ID" --format=json query --use_legacy_sql=false \
    "SELECT CONCAT(dataset_id, '.', table_id) AS t, row_count
     FROM \`$GCP_PROJECT_ID.silver.__TABLES__\`
     UNION ALL SELECT CONCAT(dataset_id, '.', table_id), row_count FROM \`$GCP_PROJECT_ID.gold.__TABLES__\`
     UNION ALL SELECT CONCAT(dataset_id, '.', table_id), row_count FROM \`$GCP_PROJECT_ID.stream.__TABLES__\`")"
manifest="$(mktemp)"
python3 - "$counts" "$(git -C "$root" rev-parse --short HEAD 2>/dev/null || echo unknown)" \
    "${exported[@]}" > "$manifest" <<'PY'
import json
import sys
from datetime import datetime, timezone

counts = {r["t"]: int(r["row_count"]) for r in json.loads(sys.argv[1])}
now = datetime.now(timezone.utc)
files = []
for item in sys.argv[3:]:
    table, path = item.split("|", 1)
    files.append({"path": path, "table": table, "rows": counts.get(table)})
print(json.dumps({
    "version": now.strftime("%Y%m%dT%H%M%SZ"),
    "exported_at": now.isoformat(timespec="seconds"),
    "commit": sys.argv[2],
    "files": files,
}, ensure_ascii=False, indent=2))
PY
"$GCLOUD" storage cp "$manifest" "gs://$GCS_BUCKET/_manifest.json" --project="$GCP_PROJECT_ID" \
    --content-type=application/json --cache-control=no-cache
rm -f "$manifest"
