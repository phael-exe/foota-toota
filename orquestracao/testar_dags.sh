#!/usr/bin/env bash
# Carrega os DAGs dentro da imagem do Airflow e roda orquestracao/tests. As regras de decisão
# (dags/foota/) têm testes próprios na suíte principal, sem Airflow (tests/test_orquestracao.py).
#
#   orquestracao/testar_dags.sh
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
imagem="$(sed -n 's/^ *image: *//p' "$aqui/docker-compose.yaml" | grep airflow | head -1)"

docker run --rm \
    -v "$aqui:/repo:ro" \
    -e AIRFLOW__CORE__LOAD_EXAMPLES=false \
    -e AIRFLOW__CORE__DAGS_FOLDER=/repo/dags \
    -e PYTHONPATH=/repo/dags \
    -e PYTHONDONTWRITEBYTECODE=1 \
    --entrypoint bash \
    "$imagem" \
    -c "pip install -q --no-warn-script-location pytest && cd /repo && python -m pytest tests -q -p no:cacheprovider"
