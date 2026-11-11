# Imagem da API do modelo (Cloud Run modelo-api): /predict, /predict/lote e /health.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/

# O Cloud Run informa a porta em $PORT
CMD exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8080}"
