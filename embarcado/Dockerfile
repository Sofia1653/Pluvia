# Coletor MQTT -> CSV/JPEG + PostgreSQL. Tambem serve para o simulador do sensor (mesmas dependencias).
# Construido a partir da raiz do repositorio (ver docker-compose.yml).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=America/Recife
WORKDIR /app

COPY embarcado/requirements.txt embarcado/requirements.txt
RUN pip install --no-cache-dir -r embarcado/requirements.txt

COPY embarcado/coletor.py embarcado/armazenamento.py embarcado/simulador.py embarcado/

CMD ["python", "embarcado/coletor.py"]
