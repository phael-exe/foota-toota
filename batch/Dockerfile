# A atualização diária do batch (scripts/atualizar_partidas.sh) como Cloud Run Job: o gcloud e o bq
# vêm da imagem oficial do Cloud SDK. O contexto do build é montado por batch/deploy_job.sh só com
# o que o job roda (scripts/, sql/ e este arquivo).
FROM gcr.io/google.com/cloudsdktool/google-cloud-cli:slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHON_BIN=python3

# O Python da imagem é o do SDK, fora do PATH: a coleta usa o do Debian, que só precisa do httpx
# além da biblioteca padrão
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-httpx \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/ scripts/
COPY sql/ sql/

ENTRYPOINT ["bash", "scripts/atualizar_partidas.sh"]
