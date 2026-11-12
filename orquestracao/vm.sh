#!/usr/bin/env bash
# A VM do Airflow (foota-toota-airflow). Rode orquestracao/infra.sh antes do primeiro `criar`.
#
#   orquestracao/vm.sh criar     # uma vez: VM com a service account airflow-orquestrador
#   orquestracao/vm.sh enviar    # copia os DAGs e o compose, sobe o Airflow e despausa os DAGs
#   orquestracao/vm.sh tunel     # interface em http://localhost:8080 (Ctrl+C fecha)
#   orquestracao/vm.sh senha     # senha do usuário admin
#   orquestracao/vm.sh ligar | parar | status
#
# A VM e2-standard-2 custa ~US$ 1,6 por dia ligada. Parada, o coletor ao vivo não roda: o plano
# B é retomar o Cloud Scheduler (streaming/deploy_coletor.sh retomar).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$root/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$root/.env"
    set +a
fi

: "${GCP_PROJECT_ID:?set GCP_PROJECT_ID in .env}"
GCLOUD="${GCLOUD_BIN:-gcloud}"
VM=foota-toota-airflow
ZONA=us-central1-a
SA="airflow-orquestrador@$GCP_PROJECT_ID.iam.gserviceaccount.com"
DAGS=(coleta_ao_vivo coleta_noticias disparar_eventos saude dataflow_liga_desliga)
project="--project=$GCP_PROJECT_ID"

na_vm() {
    "$GCLOUD" compute ssh "$VM" --zone="$ZONA" "$project" --tunnel-through-iap --quiet --command="$1"
}

case "${1:-}" in
    criar)
        "$GCLOUD" compute instances create "$VM" --zone="$ZONA" "$project" \
            --machine-type=e2-standard-2 \
            --image-family=debian-12 --image-project=debian-cloud \
            --boot-disk-size=30GB \
            --service-account="$SA" --scopes=cloud-platform \
            --tags=airflow \
            --labels=projeto=foota-toota \
            --metadata-from-file=startup-script="$root/orquestracao/instalar_docker.sh"
        echo "a instalação do Docker leva ~2 min; depois: $0 enviar"
        ;;
    enviar)
        # Os segredos nascem na VM e não saem dela; aqui só vão os DAGs e o compose
        tar -czf - -C "$root/orquestracao" --exclude=__pycache__ \
            docker-compose.yaml gerar_segredos.sh dags |
            na_vm 'mkdir -p ~/orquestracao && rm -rf ~/orquestracao/dags && tar -xzf - -C ~/orquestracao'
        na_vm "cd ~/orquestracao && ./gerar_segredos.sh 50000 && sudo docker compose up -d --wait --remove-orphans"
        for dag in "${DAGS[@]}"; do
            # o dag-processor leva alguns segundos para registrar um DAG novo
            for _ in $(seq 12); do
                if na_vm "cd ~/orquestracao && sudo docker compose exec -T airflow-scheduler airflow dags unpause $dag" >/dev/null 2>&1; then
                    echo "despausado: $dag"
                    break
                fi
                sleep 10
            done
        done
        ;;
    tunel)
        echo "interface em http://localhost:8080 (usuário admin, senha: $0 senha)"
        "$GCLOUD" compute ssh "$VM" --zone="$ZONA" "$project" --tunnel-through-iap --quiet -- -N -L 8080:localhost:8080
        ;;
    senha)
        na_vm 'cat ~/orquestracao/senhas/senhas.json'
        ;;
    ligar)
        "$GCLOUD" compute instances start "$VM" --zone="$ZONA" "$project"
        ;;
    parar)
        "$GCLOUD" compute instances stop "$VM" --zone="$ZONA" "$project"
        ;;
    status)
        "$GCLOUD" compute instances describe "$VM" --zone="$ZONA" "$project" --format='value(status)'
        na_vm 'cd ~/orquestracao && sudo docker compose ps --format "table {{.Service}}\t{{.Status}}"'
        ;;
    *)
        echo "uso: $0 criar|enviar|tunel|senha|ligar|parar|status" >&2
        exit 2
        ;;
esac
