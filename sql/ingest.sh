#!/usr/bin/env bash
# Ingestion: copies the CSVs captured from the Big Balls Data API into the Cloud Storage bucket that the
# bronze layer reads (every 01_bronze/*_create_external_table_*.sql points at gs://BUCKET/<file>.csv).
#
#   ./ingest.sh                    # uploads every CSV in data/epl (the 2026-09-08 capture)
#   ./ingest.sh /path/to/capture   # another folder with the same file names
#
# GCP_PROJECT_ID, GCS_BUCKET and GCP_REGION come from the .env at the repo root. The bucket is created
# when it does not exist yet; its location must match the BigQuery datasets (US). Uploading is
# idempotent: an existing object is overwritten by the local file of the same name. Once it finishes,
# land the files with ./run.sh 00_setup 01_bronze.
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
GCP_REGION="${GCP_REGION:-US}"
GCLOUD="${GCLOUD_BIN:-gcloud}"

src="${1:-$root/data/epl}"
if [ ! -d "$src" ]; then
    echo "no such folder: $src" >&2
    exit 2
fi

# The eight files the bronze layer reads. The other CSVs of the capture are uploaded too, as evidence
# of what the API returned, but nothing downstream depends on them.
required=(stored_matches teams leagues players stored_matches_h2h matches_weather matches_events
          stored_matches_stats_players)
for name in "${required[@]}"; do
    if [ ! -f "$src/$name.csv" ]; then
        echo "missing $src/$name.csv (needed by 01_bronze)" >&2
        exit 2
    fi
done

files=("$src"/*.csv)

if ! "$GCLOUD" storage buckets describe "gs://$GCS_BUCKET" --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
    echo "=== creating gs://$GCS_BUCKET in $GCP_REGION"
    "$GCLOUD" storage buckets create "gs://$GCS_BUCKET" \
        --project="$GCP_PROJECT_ID" \
        --location="$GCP_REGION" \
        --uniform-bucket-level-access
fi

echo "=== uploading ${#files[@]} CSV files from $src to gs://$GCS_BUCKET/"
"$GCLOUD" storage cp "${files[@]}" "gs://$GCS_BUCKET/" --project="$GCP_PROJECT_ID"

echo "=== gs://$GCS_BUCKET/ now holds"
"$GCLOUD" storage ls -l "gs://$GCS_BUCKET/" --project="$GCP_PROJECT_ID"

echo
echo "next: ./run.sh 00_setup 01_bronze   (lands the files as bronze tables with batch_id/ingested_at)"
