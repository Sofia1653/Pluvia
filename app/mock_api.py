"""Dados simulados no formato que a API de inferencia devera devolver.

Cada funcao corresponde a um endpoint planejado (indicado na docstring). Quando a API existir, basta trocar
o corpo de cada funcao por uma chamada HTTP, mantendo as mesmas colunas, e o dashboard continua funcionando.

Os valores sao gerados a partir do relogio: a mesma hora sempre produz os mesmos numeros, entao a pagina
pode ser recarregada sem que a serie "pule", e a cada atualizacao aparecem leituras novas.
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# mesmos limiares de src/alerta.py e mesmos niveis 0-3 de ModeloRisco.nivel
LIMIARES_AGUA_CM = (5.0, 15.0, 30.0)
NOMES_NIVEL = {0: "baixo", 1: "moderado", 2: "alto", 3: "muito alto"}
INTERVALO_LEITURA_S = 2

# bairros com mais registros de alagamento no dataset (regional, lat, lon, altitude media em m)
BAIRROS = {
    "Linha do Tiro": ("Norte", -8.00918, -34.90472, 31.7),
    "Varzea": ("Oeste", -8.04830, -34.97623, 34.3),
    "Jardim Sao Paulo": ("Oeste", -8.08215, -34.94419, 9.8),
    "Campina do Barreto": ("Planície", -8.01721, -34.88164, 5.7),
    "Caxanga": ("Planície", -8.02748, -34.95171, 6.8),
    "Ibura": ("Sul", -8.12015, -34.93241, 16.7),
    "Areias": ("Planície", -8.09546, -34.93185, 8.7),
    "Coqueiral": ("Oeste", -8.08720, -34.96893, 21.7),
    "Boa Viagem": ("Planície", -8.12745, -34.90258, 5.7),
    "Imbiribeira": ("Planície", -8.10547, -34.91191, 4.5),
    "San Martin": ("Planície", -8.06944, -34.92932, 6.0),
    "Beberibe": ("Norte", -8.00582, -34.89653, 25.7),
    "Brejo de Beberibe": ("Planície", -7.99868, -34.92270, 27.2),
    "Estancia": ("Planície", -8.08426, -34.93053, 7.1),
    "Torre": ("Planície", -8.04366, -34.91029, 8.5),
    "Afogados": ("Planície", -8.07777, -34.91128, 3.5),
    "Arruda": ("Planície", -8.02448, -34.88930, 5.6),
    "Boa Vista": ("Planície", -8.05782, -34.88986, 7.1),
    "Casa Forte": ("Planície", -8.03349, -34.91858, 9.6),
    "Ilha do Retiro": ("Planície", -8.06421, -34.90519, 5.0),
    "Jiquia": ("Planície", -8.08496, -34.92401, 4.5),
    "Santo Amaro": ("Planície", -8.04785, -34.87955, 5.1),
}

SENSORES = {
    "PLUVIA_01": {"topico": "pluvia/sensor01/leituras", "bairro": "Campina do Barreto", "altura_montagem_cm": 100.0},
    "PLUVIA_02": {"topico": "pluvia/sensor02/leituras", "bairro": "Afogados", "altura_montagem_cm": 120.0},
}


def nivel_agua(nivel_cm, limiares=LIMIARES_AGUA_CM):
    """Converte nivel da agua (cm) em nivel 0-3, como alerta.nivel_sensor."""
    return int(np.searchsorted(limiares, nivel_cm, side="right"))


def _chuva_mm_h(t):
    """Intensidade de chuva simulada (mm/h): pancadas que vem e vao ao longo de ~40 min."""
    s = t.timestamp() / 60.0
    pancada = max(0.0, np.sin(s / 6.5)) ** 3 * 38 + max(0.0, np.sin(s / 2.3 + 1)) ** 6 * 15
    return round(float(pancada), 1)


def _nivel_cm(t, sensor_id):
    """Nivel da agua simulado: acompanha a chuva com atraso e um pouco de ruido."""
    deslocamento = 0 if sensor_id == "PLUVIA_01" else 3.0
    atrasado = t - timedelta(minutes=4)
    base = _chuva_mm_h(atrasado) * 0.9 + _chuva_mm_h(atrasado - timedelta(minutes=3)) * 0.4
    ruido = np.random.default_rng(int(t.timestamp()) + len(sensor_id)).normal(0, 0.6)
    return max(0.0, base * 0.85 + deslocamento + ruido)


def leituras(sensor_id, minutos=30, agora=None):
    """GET /sensores/{id}/leituras?minutos=N -> timestamp, distancia_cm, nivel_agua_cm, nivel."""
    agora = (agora or datetime.now()).replace(microsecond=0)
    agora -= timedelta(seconds=agora.second % INTERVALO_LEITURA_S)
    n = minutos * 60 // INTERVALO_LEITURA_S
    tempos = [agora - timedelta(seconds=INTERVALO_LEITURA_S * i) for i in range(n)][::-1]
    altura = SENSORES[sensor_id]["altura_montagem_cm"]
    niveis = [_nivel_cm(t, sensor_id) for t in tempos]
    df = pd.DataFrame({"timestamp": tempos, "nivel_agua_cm": niveis})
    df["distancia_cm"] = (altura - df["nivel_agua_cm"]).round(2)
    df["nivel_agua_cm"] = df["nivel_agua_cm"].round(2)
    df["nivel"] = df["nivel_agua_cm"].map(nivel_agua)
    return df


def chuva(minutos=30, agora=None):
    """GET /chuva?minutos=N -> intensidade de chuva por minuto (estacao de referencia)."""
    agora = (agora or datetime.now()).replace(second=0, microsecond=0)
    tempos = [agora - timedelta(minutes=i) for i in range(minutos)][::-1]
    return pd.DataFrame({"timestamp": tempos, "chuva_mm_h": [_chuva_mm_h(t) for t in tempos]})


def previsoes(agora=None):
    """GET /previsoes -> uma linha por bairro com probabilidade, nivel do modelo e nivel combinado."""
    agora = agora or datetime.now()
    rng = np.random.default_rng(int(agora.timestamp() // 300))      # muda a cada 5 min, como uma DAG
    chuva_dia = sum(_chuva_mm_h(agora - timedelta(minutes=10 * i)) for i in range(36)) / 6
    linhas = []
    for nome, (regional, lat, lon, alt) in BAIRROS.items():
        propensao = 1.0 / (1.0 + alt / 6.0)
        logit = -7.2 + 0.045 * chuva_dia + 3.2 * propensao + rng.normal(0, 0.35)
        linhas.append({"bairro": nome, "regional": regional, "lat": lat, "lon": lon, "altitude_m": alt,
                       "probabilidade": 1.0 / (1.0 + np.exp(-logit))})
    df = pd.DataFrame(linhas)
    # niveis por posicao no ranking (top 1% -> 3, top 5% -> 2, top 15% -> 1), adaptados para poucos bairros
    pct = df["probabilidade"].rank(pct=True, ascending=False)
    df["nivel_modelo"] = np.select([pct <= 0.10, pct <= 0.25, pct <= 0.50], [3, 2, 1], 0)
    if chuva_dia < 5:                                              # sem chuva relevante, ninguem passa de moderado
        df["nivel_modelo"] = df["nivel_modelo"].clip(upper=1)
    df["nivel_sensor"] = np.nan
    for sid, info in SENSORES.items():
        ult = leituras(sid, minutos=1, agora=agora).iloc[-1]
        df.loc[df["bairro"] == info["bairro"], "nivel_sensor"] = ult["nivel"]
    df["nivel"] = df[["nivel_modelo", "nivel_sensor"]].max(axis=1).astype(int)
    df["origem"] = np.where(df["nivel_sensor"].fillna(-1) > df["nivel_modelo"], "sensor", "modelo")
    df["gerada_em"] = agora.replace(microsecond=0) - timedelta(seconds=agora.minute % 5 * 60 + agora.second)
    return df.sort_values("probabilidade", ascending=False).reset_index(drop=True)


def metricas_modelos():
    """GET /modelo/metricas -> metricas de validacao (leave-one-year-out) por modelo."""
    return pd.DataFrame([
        {"modelo": "baseline (chuva do dia)", "pr_auc": 0.009, "roc_auc": 0.871, "recall_top1": 0.20, "recall_top5": 0.38},
        {"modelo": "regressao logistica", "pr_auc": 0.021, "roc_auc": 0.902, "recall_top1": 0.27, "recall_top5": 0.51},
        {"modelo": "random forest", "pr_auc": 0.026, "roc_auc": 0.894, "recall_top1": 0.31, "recall_top5": 0.53},
        {"modelo": "gradient boosting", "pr_auc": 0.028, "roc_auc": 0.889, "recall_top1": 0.34, "recall_top5": 0.55},
    ])


def metricas_por_ano():
    """GET /modelo/metricas/ano -> PR-AUC por ano de teste do modelo em producao."""
    anos = list(range(2014, 2022))
    rng = np.random.default_rng(7)
    return pd.DataFrame({"ano": anos,
                         "pr_auc": np.round(np.clip(rng.normal(0.027, 0.012, len(anos)), 0.004, None), 3),
                         "positivos": [31, 28, 19, 6, 1, 24, 4, 3]})


def modelo_em_producao():
    """GET /modelo -> versao registrada no MLflow."""
    return {"nome": "risco_alagamento", "versao": 3, "algoritmo": "gradient boosting",
            "run_id": "a1f3c9e2b7d84b0e9f21", "treinado_em": "2026-11-10 14:32",
            "dataset": "dataset_modelagem.csv (sha256 4be1…9c0d)"}


def status_servicos(agora=None):
    """GET /saude -> estado de cada componente do docker compose."""
    agora = agora or datetime.now()
    rng = np.random.default_rng(int(agora.timestamp() // 10))
    ult_msg = {sid: leituras(sid, minutos=1, agora=agora)["timestamp"].iloc[-1] for sid in SENSORES}
    servicos = [
        ("Mosquitto (broker MQTT)", "ok", rng.integers(2, 9), "2 clientes conectados"),
        ("Coletor MQTT", "ok", rng.integers(1, 5), f"{60 // INTERVALO_LEITURA_S * len(SENSORES)} msgs/min"),
        ("PostgreSQL", "ok", rng.integers(3, 12), "leituras_sensor, previsoes"),
        ("API de inferencia", "ok", rng.integers(18, 60), "/previsoes, /sensores, /saude"),
        ("Airflow — DAG previsao_risco", "ok", None, "ultima execucao ha " + f"{agora.minute % 5} min"),
        ("MLflow", "ok", rng.integers(10, 40), "modelo risco_alagamento v3"),
    ]
    # de vez em quando a API fica lenta, para o painel ter o que mostrar
    if rng.random() < 0.25:
        nome, _, _, det = servicos[3]
        servicos[3] = (nome, "lento", int(rng.integers(600, 1500)), det)
    df = pd.DataFrame(servicos, columns=["servico", "estado", "latencia_ms", "detalhe"])
    return df, ult_msg


def execucoes_dag(agora=None, n=12):
    """GET /airflow/execucoes -> ultimas execucoes da DAG de inferencia (a cada 5 min)."""
    agora = agora or datetime.now()
    inicio = agora.replace(second=0, microsecond=0) - timedelta(minutes=agora.minute % 5)
    linhas = []
    for i in range(n):
        t = inicio - timedelta(minutes=5 * i)
        rng = np.random.default_rng(int(t.timestamp()))
        falhou = rng.random() < 0.08
        linhas.append({"execucao": t, "estado": "falhou" if falhou else "sucesso",
                       "duracao_s": round(float(rng.uniform(14, 40)), 1),
                       "previsoes_geradas": 0 if falhou else len(BAIRROS)})
    return pd.DataFrame(linhas)
