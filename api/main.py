"""API do Pluvia (esqueleto para o Docker Compose).

Por enquanto: GET /saude (banco, broker e MLflow) e GET /leituras (ultimas leituras do sensor no banco).
Ainda falta (ver Checklist_Pluvia.md): POST /risco com o modelo carregado do Model Registry, POST /imagem e GET /metricas.
Documentacao automatica em /docs.
"""
import os
import socket
import urllib.request
from datetime import datetime
from typing import Optional

import psycopg
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

DB_URL = os.environ.get("PLUVIA_DB_URL")
BROKER = os.environ.get("PLUVIA_BROKER", "mosquitto")
PORTA_BROKER = int(os.environ.get("PLUVIA_BROKER_PORTA", 1883))
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")

app = FastAPI(title="Pluvia API", version="0.1.0",
              description="Leituras do sensor e, em breve, previsao de risco de alagamento por bairro.")


class Saude(BaseModel):
    status: str
    banco: str
    broker: str
    mlflow: str


class Leitura(BaseModel):
    sensor_id: str
    ts_utc: datetime
    distancia_cm: Optional[float]
    nivel_agua_cm: Optional[float]


def _checar(funcao):
    try:
        funcao()
        return "ok"
    except Exception as erro:
        return f"erro: {erro.__class__.__name__}: {erro}"[:200]


def _banco():
    with psycopg.connect(DB_URL, connect_timeout=3) as c:
        c.execute("SELECT 1")


def _broker():
    socket.create_connection((BROKER, PORTA_BROKER), timeout=3).close()


def _mlflow():
    urllib.request.urlopen(f"{MLFLOW_URI}/health", timeout=3).read()


@app.get("/saude", response_model=Saude, summary="Status do banco, do broker MQTT e do MLflow")
def saude():
    partes = {"banco": _checar(_banco), "broker": _checar(_broker), "mlflow": _checar(_mlflow)}
    return Saude(status="ok" if all(v == "ok" for v in partes.values()) else "degradado", **partes)


@app.get("/leituras", response_model=list[Leitura], summary="Ultimas leituras do ultrassom gravadas pelo coletor")
def leituras(sensor_id: Optional[str] = None, limite: int = Query(50, ge=1, le=1000)):
    sql = "SELECT sensor_id, ts_utc, distancia_cm, nivel_agua_cm FROM leituras_sensor"
    params = []
    if sensor_id:
        sql += " WHERE sensor_id = %s"
        params.append(sensor_id)
    sql += " ORDER BY ts_utc DESC LIMIT %s"
    params.append(limite)
    try:
        with psycopg.connect(DB_URL, connect_timeout=3) as c:
            linhas = c.execute(sql, params).fetchall()
    except psycopg.Error as erro:
        raise HTTPException(status_code=503, detail=f"banco indisponivel: {erro.__class__.__name__}")
    return [Leitura(sensor_id=s, ts_utc=t, distancia_cm=d, nivel_agua_cm=n) for s, t, d, n in linhas]
