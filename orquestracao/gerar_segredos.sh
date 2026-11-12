#!/usr/bin/env bash
# Gera os segredos do Airflow (orquestracao/.env e senhas/senhas.json) se ainda não existem.
# Não sobrescreve: trocar a senha do Postgres depois de criado o banco quebra o Airflow.
#
#   orquestracao/gerar_segredos.sh [AIRFLOW_UID]
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
aleatorio() { openssl rand -hex 24; }

if [ ! -f "$aqui/.env" ]; then
    fernet="$(openssl rand -base64 32 | tr '+/' '-_')"
    umask 077
    cat > "$aqui/.env" <<FIM
AIRFLOW_UID=${1:-50000}
POSTGRES_PASSWORD=$(aleatorio)
JWT_SECRET=$(aleatorio)
API_SECRET=$(aleatorio)
FERNET_KEY=$fernet
FIM
    echo "criado $aqui/.env"
fi

mkdir -p "$aqui/senhas"
if [ ! -f "$aqui/senhas/senhas.json" ]; then
    printf '{"admin": "%s"}\n' "$(aleatorio)" > "$aqui/senhas/senhas.json"
    chmod 644 "$aqui/senhas/senhas.json"
    echo "criado $aqui/senhas/senhas.json (usuário admin)"
fi
