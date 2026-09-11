#!/usr/bin/env bash
# Runs SQL scripts against BigQuery, one statement per file, in the order given.
#
#   ./run.sh 00_setup 01_bronze          # whole folders, files in name order
#   ./run.sh 02_silver/04_create_table_matches.sql
#   ./run.sh [0-9]*                      # the entire pipeline (00 to 09)
#
# Before the first run, ./ingest.sh puts the CSVs in the bucket that 01_bronze reads.
# Each script is a template: PROJECT and BUCKET are replaced from the .env at the repo root.
# Output is mirrored to out/<folder>__<script>.txt. Any failure stops the run, so a failing
# ASSERT halts the pipeline instead of letting the next layer build on bad data.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$here")"

if [ -f "$root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$root/.env"
    set +a
fi

: "${GCP_PROJECT_ID:?set GCP_PROJECT_ID in .env}"
: "${GCS_BUCKET:?set GCS_BUCKET in .env}"
BQ="${BQ_BIN:-bq}"

if [ "$#" -eq 0 ]; then
    echo "usage: $0 <script.sql|folder> ..." >&2
    exit 2
fi

# Expand folder arguments into the .sql files they hold, sorted by name.
scripts=()
for arg in "$@"; do
    if [ -d "$arg" ]; then
        while IFS= read -r file; do
            scripts+=("$file")
        done < <(find "$arg" -maxdepth 1 -name '*.sql' | sort)
    else
        scripts+=("$arg")
    fi
done

mkdir -p "$here/out"

for file in "${scripts[@]}"; do
    name="${file#"$here/"}"
    name="${name%.sql}"
    name="${name//\//__}"
    echo "=== $name"
    sed -e "s/\bPROJECT\b/${GCP_PROJECT_ID}/g" \
        -e "s/\bBUCKET\b/${GCS_BUCKET}/g" "$file" \
      | "$BQ" query \
            --use_legacy_sql=false \
            --nouse_cache \
            --format=pretty \
            --project_id="$GCP_PROJECT_ID" 2>&1 \
      | tee "$here/out/$name.txt"
done
