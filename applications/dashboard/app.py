"""Dashboard do PLUVIA: nivel da agua (sensor ultrassonico) + analise das fotos (ESP32-CAM).

Rodar a partir da raiz do repositorio, com o coletor (src/coletor.py) gravando os dados:
    streamlit run applications/dashboard/app.py

Le os arquivos que o coletor ja grava:
    leituras.csv                     timestamp, sensor_id, distancia_cm
    data/imagens/<sensor>/*.jpg      fotos (nome = data e hora da chegada)
e grava a analise das fotos em data/analises_imagens.csv (cada foto e analisada uma vez).
"""
import csv
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import classificador

RAIZ = Path(__file__).resolve().parents[2]
ARQ_LEITURAS = RAIZ / "leituras.csv"
PASTA_IMAGENS = RAIZ / "data" / "imagens"
ARQ_ANALISES = RAIZ / "data" / "analises_imagens.csv"
COLS_ANALISE = ["arquivo", "sensor", "timestamp", "classe", "rotulo", "confianca", "nivel_minimo"]

# mesmos niveis 0-3 do modelo de risco do grupo (ModeloRisco.nivel)
NIVEIS = {0: ("Normal", "🟢"), 1: ("Atencao", "🟡"), 2: ("Alerta", "🟠"), 3: ("Critico", "🔴")}


# ------------------------------------------------------------------ logica (sem Streamlit, testavel)
def carregar_leituras(caminho=ARQ_LEITURAS):
    if not Path(caminho).exists():
        return pd.DataFrame(columns=["timestamp", "sensor_id", "distancia_cm"])
    df = pd.read_csv(caminho)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["distancia_cm"] = pd.to_numeric(df["distancia_cm"], errors="coerce")
    return df.dropna(subset=["timestamp", "distancia_cm"]).sort_values("timestamp")


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
        janela = st.slider("Leituras no gráfico", 20, 500, 150, 10)
        usar_ia = st.toggle("Analisar fotos com IA (CLIP)", value=classificador.disponivel(),
                            disabled=not classificador.disponivel())
        if not classificador.disponivel():
            st.caption("IA de imagem não instalada: veja applications/dashboard/README.md.")

    @st.fragment(run_every=5)
    def painel():
        leituras = carregar_leituras()
        fotos = listar_fotos()
        analises = carregar_analises()

        nivel_img, ultima_analise = 0, None
        if not analises.empty:
            ultima_analise = analises.iloc[-1]
            nivel_img = int(ultima_analise["nivel_minimo"])

        c1, c2, c3, c4 = st.columns(4)
        if leituras.empty:
            st.info("Aguardando leituras do sensor (o coletor está rodando?).")
            nivel_sensor = 0
        else:
            ult = leituras.iloc[-1]
            nivel = nivel_agua_cm(ult["distancia_cm"], altura)
            nivel_sensor = nivel_risco(nivel, altura, limites)
            idade = (datetime.now() - ult["timestamp"].to_pydatetime()).total_seconds()
            c1.metric("Nível da água", f"{nivel:.1f} cm")
            c2.metric("Distância medida", f"{ult['distancia_cm']:.1f} cm")
            c3.metric("Última leitura", f"há {idade:.0f} s" if idade < 3600 else ult["timestamp"].strftime("%d/%m %H:%M"))
        geral = status_geral(nivel_sensor, nivel_img)
        nome, icone = NIVEIS[geral]
        c4.metric("Status do ponto", f"{icone} {nome}", help="Maior nível entre o sensor e a análise da imagem.")

        esq, dir_ = st.columns([3, 2])
        with esq:
            st.subheader("Nível da água ao longo do tempo")
            if not leituras.empty:
                serie = leituras.tail(janela).copy()
                serie["nível da água (cm)"] = [nivel_agua_cm(d, altura) for d in serie["distancia_cm"]]
                st.line_chart(serie.set_index("timestamp")[["nível da água (cm)"]])
                st.caption(f"Sensor {leituras.iloc[-1]['sensor_id']} · {len(leituras)} leituras salvas · "
                           f"nível = altura do sensor ({altura:.0f} cm) − distância medida")
        with dir_:
            st.subheader("Última foto")
            if fotos:
                ult_foto = fotos[-1]
                st.image(str(ult_foto["caminho"]), width=360,
                         caption=f"{ult_foto['sensor']} · {ult_foto['timestamp']:%d/%m %H:%M:%S}")
                if ultima_analise is not None and ultima_analise["arquivo"] == ult_foto["arquivo"]:
                    st.markdown(f"**Análise da IA:** {ultima_analise['rotulo']} "
                                f"({100 * float(ultima_analise['confianca']):.0f}% de confiança)")
                elif usar_ia:
                    st.caption("Analisando a foto…")
            else:
                st.info("Nenhuma foto recebida ainda.")

        if not analises.empty:
            st.subheader("Fotos recentes e análise")
            recentes = analises.tail(6).iloc[::-1]
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
