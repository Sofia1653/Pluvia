"""Dashboard do PLUVIA (versao com dados simulados).

Executar a partir da raiz do repositorio:
    pip install -r app/requirements.txt
    streamlit run app/app.py

Todos os dados vem de app/mock_api.py, que imita os endpoints planejados da API de inferencia.
"""
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import mock_api as api

CORES_NIVEL = {0: "#2e9e5b", 1: "#e3b505", 2: "#ef7d22", 3: "#d7263d"}
CORES_ESTADO = {"ok": "🟢", "lento": "🟡", "falhou": "🔴", "sucesso": "🟢"}

st.set_page_config(page_title="PLUVIA — dashboard", page_icon="🌧️", layout="wide")


def rotulo_nivel(n):
    return f"{n} · {api.NOMES_NIVEL[int(n)]}"


def grafico_nivel_agua(df):
    """Serie do nivel da agua com faixas dos limiares de alerta."""
    teto = max(float(df["nivel_agua_cm"].max()) + 5, api.LIMIARES_AGUA_CM[-1] + 5)
    faixas = pd.DataFrame({"de": [0, *api.LIMIARES_AGUA_CM], "ate": [*api.LIMIARES_AGUA_CM, teto],
                           "nivel": [rotulo_nivel(i) for i in range(4)]})
    escala = alt.Scale(domain=list(faixas["nivel"]), range=list(CORES_NIVEL.values()))
    fundo = alt.Chart(faixas).mark_rect(opacity=0.12).encode(
        y=alt.Y("de:Q", title="nível da água (cm)"), y2="ate:Q",
        color=alt.Color("nivel:N", scale=escala, title="nível de alerta"))
    linha = alt.Chart(df).mark_line(color="#1f5fa8", strokeWidth=2).encode(
        x=alt.X("timestamp:T", title=None),
        y="nivel_agua_cm:Q",
        tooltip=[alt.Tooltip("timestamp:T", format="%H:%M:%S"), "nivel_agua_cm:Q", "distancia_cm:Q"])
    return (fundo + linha).properties(height=280)


# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.header("PLUVIA")
    st.caption("Risco de alagamento no Recife")
    auto = st.toggle("Atualização automática (5 s)", value=True)
    janela = st.select_slider("Janela do sensor", options=[5, 15, 30, 60], value=30, format_func=lambda m: f"{m} min")
    sensor_id = st.selectbox("Sensor", list(api.SENSORES))
    info_sensor = api.SENSORES[sensor_id]
    st.markdown(f"**Bairro:** {info_sensor['bairro']}  \n**Tópico:** `{info_sensor['topico']}`  \n"
                f"**Altura de montagem:** {info_sensor['altura_montagem_cm']:.0f} cm")
    st.divider()
    st.warning("Dados simulados (`app/mock_api.py`). Substitua pelas chamadas à API quando ela existir.", icon="⚠️")

st.title("🌧️ PLUVIA — monitoramento de risco de alagamento")


@st.fragment(run_every=5 if auto else None)
def painel():
    agora = datetime.now()
    prev = api.previsoes(agora)
    serie = api.leituras(sensor_id, minutos=janela, agora=agora)
    chuva = api.chuva(minutos=janela, agora=agora)
    servicos, ult_msg = api.status_servicos(agora)
    ultima = serie.iloc[-1]
    anterior = serie.iloc[-30] if len(serie) > 30 else serie.iloc[0]

    st.caption(f"Atualizado em {agora:%d/%m/%Y %H:%M:%S} · previsões geradas em {prev['gerada_em'].iloc[0]:%H:%M}")

    # ---------------------------------------------------------- indicadores
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(f"Nível da água · {sensor_id}", f"{ultima['nivel_agua_cm']:.1f} cm",
              f"{ultima['nivel_agua_cm'] - anterior['nivel_agua_cm']:+.1f} cm (1 min)", delta_color="inverse")
    c2.metric("Alerta no sensor", rotulo_nivel(ultima["nivel"]))
    c3.metric("Chuva agora", f"{chuva['chuva_mm_h'].iloc[-1]:.1f} mm/h")
    c4.metric("Bairros em risco alto ou muito alto", int((prev["nivel"] >= 2).sum()), f"de {len(prev)} monitorados",
              delta_color="off")
    problemas = int((servicos["estado"] != "ok").sum())
    c5.metric("Serviços", f"{len(servicos) - problemas}/{len(servicos)} ok",
              "tudo normal" if problemas == 0 else f"{problemas} com alerta",
              delta_color="normal" if problemas == 0 else "inverse")

    aba_sensor, aba_prev, aba_modelo, aba_mon = st.tabs(
        ["📡 Sensor em tempo real", "🗺️ Previsões por bairro", "📈 Métricas do modelo", "🩺 Monitoramento"])

    # ---------------------------------------------------------- sensor
    with aba_sensor:
        esq, dir_ = st.columns([2, 1])
        with esq:
            st.subheader("Nível da água")
            st.altair_chart(grafico_nivel_agua(serie), width="stretch")
            st.subheader("Chuva (estação de referência)")
            st.altair_chart(alt.Chart(chuva).mark_area(color="#5b8fd6", opacity=0.6).encode(
                x=alt.X("timestamp:T", title=None), y=alt.Y("chuva_mm_h:Q", title="mm/h")).properties(height=160),
                width="stretch")
        with dir_:
            st.subheader("Últimas mensagens MQTT")
            ult = serie.tail(12).iloc[::-1].copy()
            ult["timestamp"] = ult["timestamp"].dt.strftime("%H:%M:%S")
            ult["nivel"] = ult["nivel"].map(rotulo_nivel)
            st.dataframe(ult[["timestamp", "distancia_cm", "nivel_agua_cm", "nivel"]], hide_index=True,
                         width="stretch")
            st.caption(f"Payload: `{{\"sensor_id\": \"{sensor_id}\", \"distancia_cm\": {ultima['distancia_cm']:.2f}}}` "
                       f"· nível = altura de montagem − distância")

    # ---------------------------------------------------------- previsoes
    with aba_prev:
        esq, dir_ = st.columns([3, 2])
        with esq:
            st.subheader("Mapa de risco")
            mapa = prev.copy()
            mapa["cor"] = mapa["nivel"].map(CORES_NIVEL)
            mapa["tamanho"] = 120 + mapa["nivel"] * 110
            st.map(mapa, latitude="lat", longitude="lon", color="cor", size="tamanho", zoom=11, height=420)
            st.caption(" ".join(f"<span style='color:{c}'>●</span> {rotulo_nivel(n)}" for n, c in CORES_NIVEL.items()),
                       unsafe_allow_html=True)
        with dir_:
            st.subheader("Ranking de risco")
            tab = prev[["bairro", "regional", "probabilidade", "nivel_modelo", "nivel_sensor", "nivel", "origem"]].copy()
            tab["nivel"] = tab["nivel"].map(rotulo_nivel)
            st.dataframe(tab, hide_index=True, width="stretch", height=420, column_config={
                "probabilidade": st.column_config.ProgressColumn("probabilidade", format="%.4f", min_value=0,
                                                                 max_value=float(prev["probabilidade"].max())),
                "nivel_modelo": st.column_config.NumberColumn("modelo", format="%d"),
                "nivel_sensor": st.column_config.NumberColumn("sensor", format="%d"),
                "nivel": "alerta final"})
        st.info("O alerta final é o **maior** entre o nível do modelo (ranking de probabilidade) e o do sensor, "
                "como em `src/alerta.py`. Bairros sem sensor usam só o modelo.", icon="ℹ️")

    # ---------------------------------------------------------- modelo
    with aba_modelo:
        mod = api.modelo_em_producao()
        st.markdown(f"**Modelo em produção:** {mod['algoritmo']} · **MLflow:** `{mod['nome']}` v{mod['versao']} "
                    f"(run `{mod['run_id'][:8]}`) · **treinado em** {mod['treinado_em']} · **dataset:** {mod['dataset']}")
        met = api.metricas_modelos()
        esq, dir_ = st.columns(2)
        with esq:
            st.subheader("Comparação de modelos (validação por ano)")
            longo = met.melt("modelo", ["pr_auc", "recall_top5"], var_name="métrica", value_name="valor")
            st.altair_chart(alt.Chart(longo).mark_bar().encode(
                x=alt.X("valor:Q"), y=alt.Y("modelo:N", sort=list(met["modelo"]), title=None),
                color=alt.Color("modelo:N", legend=None), row=alt.Row("métrica:N", title=None),
                tooltip=["modelo", "métrica", alt.Tooltip("valor:Q", format=".3f")]
            ).properties(height=130).resolve_scale(x="independent"), width="stretch")
        with dir_:
            st.subheader("Estabilidade: PR-AUC por ano de teste")
            ano = api.metricas_por_ano()
            st.altair_chart(alt.Chart(ano).mark_bar(color="#1f5fa8").encode(
                x=alt.X("ano:O"), y=alt.Y("pr_auc:Q", title="PR-AUC"),
                opacity=alt.condition(alt.datum.positivos >= 5, alt.value(1.0), alt.value(0.35)),
                tooltip=["ano", "pr_auc", "positivos"]).properties(height=300), width="stretch")
            st.caption("Barras claras: anos com menos de 5 positivos (resultado pouco confiável).")
        st.dataframe(met.style.format({c: "{:.3f}" for c in ["pr_auc", "roc_auc", "recall_top1", "recall_top5"]}),
                     hide_index=True, width="stretch")

    # ---------------------------------------------------------- monitoramento
    with aba_mon:
        esq, dir_ = st.columns([3, 2])
        with esq:
            st.subheader("Saúde dos serviços")
            s = servicos.copy()
            s["estado"] = s["estado"].map(lambda e: f"{CORES_ESTADO[e]} {e}")
            st.dataframe(s, hide_index=True, width="stretch", column_config={
                "latencia_ms": st.column_config.NumberColumn("latência (ms)", format="%d")})
            st.subheader("Última mensagem por sensor")
            for sid, t in ult_msg.items():
                idade = (agora - t).total_seconds()
                st.write(f"{'🟢' if idade < 30 else '🔴'} **{sid}** — há {idade:.0f} s ({t:%H:%M:%S})")
        with dir_:
            st.subheader("Execuções da DAG `previsao_risco`")
            dag = api.execucoes_dag(agora)
            dag["execucao"] = dag["execucao"].dt.strftime("%H:%M")
            dag["estado"] = dag["estado"].map(lambda e: f"{CORES_ESTADO[e]} {e}")
            st.dataframe(dag, hide_index=True, width="stretch")


painel()
