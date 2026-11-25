"""API do Pluvia: monitoramento, previsao de risco e classificacao de imagens."""

import os
import socket
import urllib.request
import logging
from datetime import datetime, date
from typing import Optional
from functools import lru_cache
from io import BytesIO

import mlflow
import mlflow.sklearn
import pandas as pd
import psycopg

from psycopg.rows import dict_row
from mlflow.tracking import MlflowClient
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field, ConfigDict
from PIL import Image, UnidentifiedImageError
from classificador import classificar

DB_URL = os.environ.get("PLUVIA_DB_URL")
BROKER = os.environ.get("PLUVIA_BROKER", "mosquitto")
PORTA_BROKER = int(os.environ.get("PLUVIA_BROKER_PORTA", 1883))
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")

MODEL_NAME = os.environ.get("PLUVIA_MODEL_NAME", "risco_alagamento")
MODEL_ALIAS = os.environ.get("PLUVIA_MODEL_ALIAS", "campeao")

LIMITE_IMAGEM = 10 * 1024 * 1024

logger = logging.getLogger(__name__)

mlflow.set_tracking_uri(MLFLOW_URI)
client = MlflowClient()

app = FastAPI(
    title="Pluvia API",
    version="1.0.0",
    description="Monitoramento de sensores, previsao de risco de alagamento e classificacao de imagens."
)


class Saude(BaseModel):
    status: str
    banco: str
    broker: str
    mlflow: str
    modelo: str


class Leitura(BaseModel):
    sensor_id: str
    ts_utc: datetime
    distancia_cm: Optional[float]
    nivel_agua_cm: Optional[float]


class RiscoRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    bairro: str = Field(min_length=1, max_length=100)
    data: date


class RiscoResponse(BaseModel):
    bairro: str
    data: date
    probabilidade: float = Field(ge=0, le=1)
    nivel_risco: int = Field(ge=0, le=3)
    nivel_agua_cm: Optional[float]
    modelo: str
    versao: str


class ImagemResponse(BaseModel):
    classe: str
    rotulo: str
    confianca: float = Field(ge=0, le=1)
    nivel_minimo: int = Field(ge=0, le=3)


def _checar(funcao):
    try:
        funcao()
        return "ok"
    except Exception as erro:
        logger.exception("Falha na verificacao de saude")
        return f"erro: {erro.__class__.__name__}"


def _banco():
    with psycopg.connect(DB_URL, connect_timeout=3) as conexao:
        conexao.execute("SELECT 1")


def _broker():
    socket.create_connection(
        (BROKER, PORTA_BROKER), timeout=3
    ).close()


def _mlflow():
    with urllib.request.urlopen(
        f"{MLFLOW_URI}/health", timeout=3
    ) as resposta:
        resposta.read()


@lru_cache(maxsize=1)
def carregar_modelo(nome, versao):
    return mlflow.sklearn.load_model(
        f"models:/{nome}/{versao}"
    )


def _modelo():
    versao = client.get_model_version_by_alias(
        MODEL_NAME, MODEL_ALIAS
    )

    carregar_modelo(MODEL_NAME, versao.version)


def buscar_dados_bairro(bairro, data):
    sql = """
        SELECT *
        FROM dataset_historico
        WHERE LOWER(bairro) = LOWER(%s)
        AND data = %s
    """

    with psycopg.connect(
        DB_URL, connect_timeout=3, row_factory=dict_row
    ) as conexao:
        linhas = conexao.execute(
            sql, (bairro, data)
        ).fetchall()

    if not linhas:
        raise HTTPException(
            status_code=404,
            detail="Dados nao encontrados para o bairro e data informados"
        )

    return pd.DataFrame(linhas)


def buscar_nivel_agua(bairro, data):
    sql = """
        SELECT l.nivel_agua_cm
        FROM leituras_sensor l
        JOIN unidades u ON l.unidade_id = u.unidade_id
        WHERE LOWER(u.nome_exibicao) = LOWER(%s)
        AND (l.ts_utc AT TIME ZONE 'America/Recife')::date = %s
        ORDER BY l.ts_utc DESC
        LIMIT 1
    """

    with psycopg.connect(DB_URL, connect_timeout=3) as conexao:
        leitura = conexao.execute(
            sql, (bairro, data)
        ).fetchone()

    return leitura[0] if leitura else None


@app.get(
    "/saude",
    response_model=Saude,
    summary="Status dos servicos e do modelo"
)
def saude():
    partes = {
        "banco": _checar(_banco),
        "broker": _checar(_broker),
        "mlflow": _checar(_mlflow),
        "modelo": _checar(_modelo)
    }

    return Saude(
        status="ok" if all(v == "ok" for v in partes.values())
        else "degradado",
        **partes
    )


@app.get(
    "/leituras",
    response_model=list[Leitura],
    summary="Ultimas leituras do sensor"
)
def leituras(
    sensor_id: Optional[str] = None,
    limite: int = Query(50, ge=1, le=1000)
):
    sql = """
        SELECT sensor_id, ts_utc, distancia_cm, nivel_agua_cm
        FROM leituras_sensor
    """

    params = []

    if sensor_id:
        sql += " WHERE sensor_id = %s"
        params.append(sensor_id)

    sql += " ORDER BY ts_utc DESC LIMIT %s"
    params.append(limite)

    try:
        with psycopg.connect(DB_URL, connect_timeout=3) as conexao:
            linhas = conexao.execute(sql, params).fetchall()

    except psycopg.Error:
        logger.exception("Erro ao consultar leituras")

        raise HTTPException(
            status_code=503,
            detail="Banco de dados indisponivel"
        )

    return [
        Leitura(
            sensor_id=s,
            ts_utc=t,
            distancia_cm=d,
            nivel_agua_cm=n
        )
        for s, t, d, n in linhas
    ]


@app.get("/metricas", summary="Metricas do modelo ativo")
def metricas():
    try:
        modelo = client.get_model_version_by_alias(
            MODEL_NAME, MODEL_ALIAS
        )

        run = client.get_run(modelo.run_id)
        vinculo_direto = True

        if not run.data.metrics:
            vinculo_direto = False

            nomes_runs = {
                "risco_alagamento": "final_logistica_cenarioA",
                "risco_alagamento_cenario_B": "final_logistica_cenarioB"
            }

            nome_run = nomes_runs.get(MODEL_NAME)

            experimento = client.get_experiment_by_name(
                "alagamento_modelagem"
            )

            if not experimento or not nome_run:
                raise HTTPException(
                    status_code=404,
                    detail="Metricas nao encontradas"
                )

            runs = client.search_runs(
                experiment_ids=[experimento.experiment_id],
                filter_string=(
                    f"tags.mlflow.runName = '{nome_run}' "
                    "AND attributes.status = 'FINISHED'"
                ),
                order_by=["attributes.start_time DESC"],
                max_results=1
            )

            if not runs or not runs[0].data.metrics:
                raise HTTPException(
                    status_code=404,
                    detail="Metricas nao encontradas"
                )

            run = runs[0]

        return {
            "modelo": MODEL_NAME,
            "versao": modelo.version,
            "alias": MODEL_ALIAS,
            "run_id_metricas": run.info.run_id,
            "metricas_vinculadas_ao_modelo": vinculo_direto,
            "metricas": run.data.metrics
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Erro ao consultar metricas")

        raise HTTPException(
            status_code=503,
            detail="Metricas do modelo indisponiveis"
        )


@app.post(
    "/risco",
    response_model=RiscoResponse,
    summary="Previsao de risco de alagamento"
)
def risco(requisicao: RiscoRequest):
    try:
        df = buscar_dados_bairro(
            requisicao.bairro,
            requisicao.data
        )

        versao = client.get_model_version_by_alias(
            MODEL_NAME, MODEL_ALIAS
        )

        modelo = carregar_modelo(
            MODEL_NAME, versao.version
        )

        probabilidade = float(modelo.prever(df)[0])
        nivel = int(modelo.nivel(df)[0])

        nivel_agua = buscar_nivel_agua(
            requisicao.bairro,
            requisicao.data
        )

        return RiscoResponse(
            bairro=requisicao.bairro,
            data=requisicao.data,
            probabilidade=probabilidade,
            nivel_risco=nivel,
            nivel_agua_cm=nivel_agua,
            modelo=MODEL_NAME,
            versao=versao.version
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Erro na previsao de risco")

        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel realizar a previsao"
        )


@app.post(
    "/imagem",
    response_model=ImagemResponse,
    summary="Classificacao de imagem do sensor"
)
def imagem(arquivo: UploadFile = File(...)):
    if arquivo.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=415,
            detail="Envie uma imagem JPEG ou PNG"
        )

    try:
        conteudo = arquivo.file.read(LIMITE_IMAGEM + 1)

        if len(conteudo) > LIMITE_IMAGEM:
            raise HTTPException(
                status_code=413,
                detail="A imagem deve possuir ate 10 MB"
            )

        with Image.open(BytesIO(conteudo)) as img:
            if img.format not in ["JPEG", "PNG"]:
                raise HTTPException(
                    status_code=415,
                    detail="Formato de imagem invalido"
                )

            img.verify()

        resultado = classificar(BytesIO(conteudo))

        if resultado is None:
            raise HTTPException(
                status_code=503,
                detail="Classificador indisponivel"
            )

        return resultado

    except HTTPException:
        raise

    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(
            status_code=400,
            detail="Imagem invalida ou corrompida"
        )

    except Exception:
        logger.exception("Erro na classificacao de imagem")

        raise HTTPException(
            status_code=500,
            detail="Erro na classificacao da imagem"
        )