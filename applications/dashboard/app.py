"""Dashboard do PLUVIA: nivel da agua (sensor ultrassonico) + analise das fotos (ESP32-CAM).

Rodar a partir da raiz do repositorio, com o coletor (src/coletor.py) gravando os dados:
    streamlit run applications/dashboard/app.py

Le as leituras no PostgreSQL e os arquivos que o coletor ja grava:
    data/imagens/<sensor>/*.jpg      fotos (nome = data e hora da chegada)
e grava a analise das fotos em data/analises_imagens.csv (cada foto e analisada uma vez).
"""
import csv
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg
import streamlit as st

import classificador

RAIZ = Path(__file__).resolve().parents[2]
PASTA_IMAGENS = RAIZ / "data" / "imagens"
ARQ_ANALISES = RAIZ / "data" / "analises_imagens.csv"
COLS_ANALISE = ["arquivo", "sensor", "timestamp", "classe", "rotulo", "confianca", "nivel_minimo"]
FUSO = ZoneInfo("America/Recife")
LIMITE_SEM_LEITURA_S = 600

# mesmos niveis 0-3 do modelo de risco do grupo (ModeloRisco.nivel)
NIVEIS = {0: ("Normal", "🟢"), 1: ("Atencao", "🟡"), 2: ("Alerta", "🟠"), 3: ("Critico", "🔴")}


# ------------------------------------------------------------------ logica (sem Streamlit, testavel)
def conectar_banco():
    url = os.environ.get("PLUVIA_DB_URL")
    if not url:
        raise ValueError("Configure PLUVIA_DB_URL para consultar as leituras")
    return psycopg.connect(url, connect_timeout=3)


def listar_sensores(conn):
    return [linha[0] for linha in conn.execute(
        "SELECT DISTINCT sensor_id FROM leituras_sensor ORDER BY sensor_id"
    ).fetchall()]


def carregar_leituras(conn, sensor, inicio, fim):
    inicio_ts = datetime.combine(inicio, time.min, tzinfo=FUSO)
    fim_ts = datetime.combine(fim + timedelta(days=1), time.min, tzinfo=FUSO)
    linhas = conn.execute(
        "SELECT ts_utc, sensor_id, distancia_cm FROM leituras_sensor "
        "WHERE sensor_id = %s AND ts_utc >= %s AND ts_utc < %s "
        "ORDER BY ts_utc, leitura_id", (sensor, inicio_ts, fim_ts),
    ).fetchall()
    df = pd.DataFrame(linhas, columns=["timestamp", "sensor_id", "distancia_cm"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.tz_convert(FUSO)
    df["distancia_cm"] = pd.to_numeric(df["distancia_cm"], errors="coerce")
    return df.dropna(subset=["timestamp", "distancia_cm"]).sort_values("timestamp")


def indicadores_sensor(conn, sensor, agora):
    ultima = conn.execute(
        "SELECT ts_utc, distancia_cm FROM leituras_sensor WHERE sensor_id = %s "
        "ORDER BY ts_utc DESC, leitura_id DESC LIMIT 1", (sensor,),
    ).fetchone()
    inicio_dia = datetime.combine(agora.astimezone(FUSO).date(), time.min, tzinfo=FUSO)
    fim_dia = inicio_dia + timedelta(days=1)
    menor_distancia = conn.execute(
        "SELECT MIN(distancia_cm) FROM leituras_sensor "
        "WHERE sensor_id = %s AND ts_utc >= %s AND ts_utc < %s",
        (sensor, inicio_dia, fim_dia),
    ).fetchone()[0]
    return ultima, menor_distancia


def idade_leitura(timestamp, agora):
    return max(0, (agora - timestamp).total_seconds())


def tempo_decorrido(segundos):
    segundos = int(segundos)
    if segundos < 60:
        return f"{segundos} s"
    if segundos < 3600:
        return f"{segundos // 60} min {segundos % 60} s"
    if segundos < 86400:
        return f"{segundos // 3600} h {(segundos % 3600) // 60} min"
    return f"{segundos // 86400} d {(segundos % 86400) // 3600} h"


def nivel_agua_cm(distancia_cm, altura_sensor_cm):
    """Sensor apontado para baixo: quanto menor a distancia, mais alta a agua."""
    return max(0.0, float(altura_sensor_cm) - float(distancia_cm))


def nivel_risco(nivel_cm, altura_sensor_cm, limites_pct=(25, 50, 75)):
    """0 Normal, 1 Atencao, 2 Alerta, 3 Critico, pela fracao da altura ocupada pela agua."""
    pct = 100 * nivel_cm / altura_sensor_cm if altura_sensor_cm > 0 else 0
    return sum(pct >= l for l in limites_pct)


def listar_fotos(pasta=PASTA_IMAGENS):
    fotos = []
    for arq in Path(pasta).glob("*/*.jpg"):
        try:
            ts = datetime.strptime(arq.stem, "%Y%m%d_%H%M%S_%f")
        except ValueError:
            ts = datetime.fromtimestamp(arq.stat().st_mtime)
        fotos.append({"arquivo": str(arq.relative_to(RAIZ)), "sensor": arq.parent.name, "timestamp": ts,
                      "caminho": arq})
    return sorted(fotos, key=lambda f: f["timestamp"])


def carregar_analises(caminho=ARQ_ANALISES):
    if not Path(caminho).exists():
        return pd.DataFrame(columns=COLS_ANALISE)
    return pd.read_csv(caminho)


def analisar_novas(fotos, caminho=ARQ_ANALISES, limite=5):
    """Classifica fotos ainda sem analise (no maximo 'limite' por atualizacao, para nao travar a tela)."""
    feitas = set(carregar_analises(caminho)["arquivo"])
    novas = [f for f in fotos if f["arquivo"] not in feitas][-limite:]
    if not novas:
        return 0
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    novo_arquivo = not Path(caminho).exists()
    n = 0
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo_arquivo:
            w.writerow(COLS_ANALISE)
        for foto in novas:
            r = classificador.classificar(foto["caminho"])
            if r is None:
                break
            w.writerow([foto["arquivo"], foto["sensor"], foto["timestamp"].isoformat(timespec="seconds"),
                        r["classe"], r["rotulo"], r["confianca"], r["nivel_minimo"]])
            n += 1
    return n


def status_geral(nivel_sensor, nivel_imagem):
    """O alerta final e o maior entre o nivel da agua e o que a imagem indica."""
    return max(nivel_sensor, nivel_imagem or 0)


def nivel_imagem_recente(fotos, analises, camera, agora):
    """Usa apenas a analise da ultima foto recente da camera associada."""
    fotos_camera = [foto for foto in fotos if foto["sensor"] == camera]
    if not fotos_camera or analises.empty:
        return 0, None
    foto = fotos_camera[-1]
    correspondentes = analises[analises["arquivo"] == foto["arquivo"]]
    if correspondentes.empty:
        return 0, None
    analise = correspondentes.iloc[-1]
    idade = (agora - foto["timestamp"]).total_seconds()
    nivel = int(analise["nivel_minimo"]) if 0 <= idade <= LIMITE_SEM_LEITURA_S else 0
    return nivel, analise


# ------------------------------------------------------------------ interface
def main():
    st.set_page_config(page_title="PLUVIA", page_icon="🌧️", layout="wide")
    st.title("🌧️ PLUVIA — monitoramento do ponto crítico")

    with st.sidebar:
        st.header("Configuração do ponto")
        altura = st.number_input("Altura do sensor até o fundo seco (cm)", 5.0, 400.0, 30.0, 1.0,
                                 help="Distância medida pelo sensor quando não há água.")
        atencao = st.slider("Atenção a partir de (% da altura)", 0, 100, 25)
        alerta = st.slider("Alerta a partir de (% da altura)", 0, 100, 50)
        critico = st.slider("Crítico a partir de (% da altura)", 0, 100, 75)
        limites = (atencao, alerta, critico)
        limites_validos = atencao < alerta < critico
        if not limites_validos:
            st.error("Configure os limites em ordem crescente: atenção, alerta e crítico.")
        usar_ia = st.toggle("Analisar fotos com IA (CLIP)", value=classificador.disponivel(),
                            disabled=not classificador.disponivel())
        if not classificador.disponivel():
            st.caption("IA de imagem não instalada: veja applications/dashboard/README.md.")

    @st.fragment(run_every=5)
    def painel():
        agora = datetime.now(timezone.utc)
        hoje = agora.astimezone(FUSO).date()
        try:
            with conectar_banco() as conn:
                sensores = listar_sensores(conn)
                if not sensores:
                    st.info("Aguardando a primeira leitura de um sensor.")
                    return
                sensor = st.selectbox("Sensor", sensores, key="sensor_selecionado")
                datas = st.columns(2)
                inicio = datas[0].date_input("Data inicial", value=hoje - timedelta(days=6), key="data_inicial")
                fim = datas[1].date_input("Data final", value=hoje, key="data_final")
                if inicio > fim:
                    st.warning("A data inicial deve ser anterior ou igual à data final.")
                    return
                leituras = carregar_leituras(conn, sensor, inicio, fim)
                ultima, menor_distancia = indicadores_sensor(conn, sensor, agora)
        except (psycopg.Error, ValueError):
            st.error("Não foi possível consultar o PostgreSQL. Verifique a conexão e PLUVIA_DB_URL.")
            return
        fotos = listar_fotos()
        analises = carregar_analises()
        cameras = sorted({foto["sensor"] for foto in fotos})
        opcoes_cameras = ["Nenhuma"] + cameras
        padrao = opcoes_cameras.index(sensor) if sensor in cameras else 0
        camera = st.selectbox("Câmera associada ao sensor", opcoes_cameras, index=padrao,
                              key=f"camera_{sensor}",
                              help="Escolha explicitamente a câmera deste ponto quando os identificadores forem diferentes.")
        fotos_camera = [foto for foto in fotos if foto["sensor"] == camera]
        nivel_img, ultima_analise = nivel_imagem_recente(fotos, analises, camera, datetime.now())

        c1, c2, c3, c4, c5 = st.columns(5)
        if ultima is None:
            nivel_sensor = None
        else:
            timestamp, distancia = ultima
            nivel = nivel_agua_cm(distancia, altura)
            nivel_sensor = nivel_risco(nivel, altura, limites)
            idade = idade_leitura(timestamp, agora)
            c1.metric("Nível da água", f"{nivel:.1f} cm")
            c2.metric("Distância medida", f"{distancia:.1f} cm")
            c3.metric("Última leitura", f"há {tempo_decorrido(idade)}")
            if idade > LIMITE_SEM_LEITURA_S:
                st.warning(f"O sensor {sensor} não envia leituras há mais de 10 minutos. Verifique a conexão.")
                nivel_sensor = None
        c4.metric("Máximo de hoje", f"{nivel_agua_cm(menor_distancia, altura):.1f} cm" if menor_distancia is not None else "Sem leituras")
        if not limites_validos:
            c5.metric("Status do ponto", "Limites inválidos")
        elif nivel_sensor is None:
            c5.metric("Status do ponto", "Sem leitura recente")
        else:
            geral = status_geral(nivel_sensor, nivel_img)
            nome, icone = NIVEIS[geral]
            c5.metric("Status do ponto", f"{icone} {nome}", help="Maior nível entre o sensor e a análise da imagem associada ao mesmo identificador.")

        esq, dir_ = st.columns([3, 2])
        with esq:
            st.subheader("Nível da água ao longo do tempo")
            if not leituras.empty:
                serie = leituras.copy()
                serie["nível da água (cm)"] = [nivel_agua_cm(d, altura) for d in serie["distancia_cm"]]
                st.line_chart(serie.set_index("timestamp")[["nível da água (cm)"]])
                st.caption(f"Sensor {sensor} · {len(leituras)} leituras no período · "
                           f"nível = altura do sensor ({altura:.0f} cm) − distância medida")
            else:
                st.info("Nenhuma leitura para este sensor no período selecionado.")
        with dir_:
            st.subheader("Última foto")
            if fotos_camera:
                ult_foto = fotos_camera[-1]
                st.image(str(ult_foto["caminho"]), width=360,
                         caption=f"{ult_foto['sensor']} · {ult_foto['timestamp']:%d/%m %H:%M:%S}")
                if ultima_analise is not None and ultima_analise["arquivo"] == ult_foto["arquivo"]:
                    st.markdown(f"**Análise da IA:** {ultima_analise['rotulo']} "
                                f"({100 * float(ultima_analise['confianca']):.0f}% de confiança)")
                elif usar_ia:
                    st.caption("Analisando a foto…")
            else:
                st.info("Selecione a câmera associada para ver suas fotos." if cameras else "Nenhuma foto recebida ainda.")

        if not analises.empty:
            recentes = analises[analises["sensor"] == camera].tail(6).iloc[::-1]
            if not recentes.empty:
                st.subheader("Fotos recentes e análise")
                cols = st.columns(len(recentes))
                for col, (_, a) in zip(cols, recentes.iterrows()):
                    caminho = RAIZ / a["arquivo"]
                    if caminho.exists():
                        col.image(str(caminho), width=180)
                    col.caption(f"{a['timestamp'][11:19]} · {a['rotulo']} ({100 * float(a['confianca']):.0f}%)")

        # analise por ultimo: a tela aparece antes, e o resultado entra na proxima atualizacao (5 s).
        # Na primeira vez o CLIP e baixado (~600 MB), o que pode levar alguns minutos.
        if usar_ia and fotos:
            with st.spinner("Analisando fotos novas com a IA..."):
                analisar_novas(fotos)

    painel()


if __name__ == "__main__":
    main()
