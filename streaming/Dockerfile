# Imagem do coletor ao vivo (Cloud Run Job foota-toota-coletor). Cada execução consulta a API uma vez,
# publica as partidas que mudaram e termina; o Cloud Scheduler dispara a cada 5 minutos.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements-producer.txt .
RUN pip install --no-cache-dir -r requirements-producer.txt

COPY producer.py .

CMD ["python", "producer.py", "live", "--uma-vez"]
