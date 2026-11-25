# Dashboard Streamlit. Sem a IA de imagem por padrao (torch/transformers somam ~2 GB);
# para incluir: docker compose build --build-arg COM_IA=1 dashboard
FROM python:3.11-slim

ARG COM_IA=0
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=America/Recife
WORKDIR /app

COPY applications/dashboard/requirements.txt applications/dashboard/requirements-ia.txt applications/dashboard/
RUN pip install --no-cache-dir -r applications/dashboard/requirements.txt \
 && if [ "$COM_IA" = "1" ]; then pip install --no-cache-dir -r applications/dashboard/requirements-ia.txt; fi

COPY applications/dashboard/app.py applications/dashboard/classificador.py applications/dashboard/

EXPOSE 8501
CMD ["streamlit", "run", "applications/dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
