"""DAG de verificacao: confirma que o Airflow alcanca o banco do Pluvia e conta as leituras da ultima hora.

Serve para validar a infraestrutura do Compose. As DAGs de ingestao, preparacao, inferencia e retreino
(Checklist_Pluvia.md, Fase 4) entram nesta mesma pasta e podem importar o codigo de src/ (no PYTHONPATH).
"""
import os
from datetime import datetime, timedelta

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator


def contar_leituras():
    with psycopg2.connect(os.environ["PLUVIA_DB_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*), max(ts_utc) FROM leituras_sensor WHERE ts_utc > now() - interval '1 hour'")
        n, ultima = cur.fetchone()
    print(f"leituras na ultima hora: {n}; ultima: {ultima}")
    if n == 0:
        raise ValueError("nenhuma leitura do sensor na ultima hora (coletor ou ESP32 parados?)")
    return n


with DAG(
    dag_id="pluvia_saude",
    description="Verifica a chegada de leituras do sensor no banco",
    start_date=datetime(2026, 11, 1),
    schedule=timedelta(minutes=15),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=1)},
    tags=["pluvia", "infra"],
) as dag:
    PythonOperator(task_id="contar_leituras", python_callable=contar_leituras)
