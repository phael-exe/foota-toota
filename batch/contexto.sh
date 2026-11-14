#!/usr/bin/env bash
# Monta em <pasta> o contexto do build da imagem do Job do batch: o Dockerfile, scripts/ e sql/,
# sem as saídas do run.sh nem caches. O .dockerignore da raiz tira o sql/, e o Cloud Build usa o
# docker sem .dockerignore por Dockerfile; o deploy (batch/deploy_job.sh) e o CI usam este script.
#
#   batch/contexto.sh <pasta>
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
destino="${1:?uso: $0 <pasta>}"

mkdir -p "$destino"
cp "$root/batch/Dockerfile" "$destino/"
cp -r "$root/scripts" "$root/sql" "$destino/"
rm -rf "$destino/sql/out"
find "$destino" -name __pycache__ -type d -prune -exec rm -rf {} +
