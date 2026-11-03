FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Copia metadados e dependências
COPY pyproject.toml README.md ./

# Instala bibliotecas necessárias no container
RUN pip install --no-cache-dir \
    httpx \
    google-cloud-storage \
    google-cloud-bigquery \
    .

# Copia código-fonte e scripts de ingestão
COPY src/ src/
COPY scripts/ scripts/

# Comando padrão do Cloud Run Job: executa a coleta de notícias com corpo completo
CMD ["python", "scripts/fetch_news.py"]

