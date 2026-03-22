#!/usr/bin/env python3
"""Interface simples para visualizar condomínios e copiar a lista CSV."""

from __future__ import annotations

import io
from dataclasses import asdict

import pandas as pd
import streamlit as st

from condo_geo_crawler import CIDADES_PADRAO, TERMOS_BUSCA_PADRAO, CondoCrawler


st.set_page_config(page_title="Visualizador de Condomínios", layout="wide")
st.title("🏘️ Visualizador de Condomínios de Alto Padrão")
st.caption("Colete, visualize no mapa e copie/exporte as georreferências em CSV.")


@st.cache_data(show_spinner=False)
def dataframe_para_csv(df: pd.DataFrame) -> str:
    return df.to_csv(index=False)


def resultados_para_dataframe(resultados) -> pd.DataFrame:
    linhas = []
    for item in resultados:
        dado = asdict(item)
        linhas.append(
            {
                "Nome do Condomínio": dado["nome"],
                "Cidade": dado["cidade"],
                "Endereço Completo": dado["endereco"],
                "Latitude": dado["latitude"],
                "Longitude": dado["longitude"],
            }
        )
    return pd.DataFrame(linhas)


with st.sidebar:
    st.header("Configuração")
    api_key = st.text_input("Google API Key", type="password", help="Precisa de acesso à Places API.")
    cidades = st.multiselect("Cidades alvo", options=CIDADES_PADRAO, default=CIDADES_PADRAO)
    termos_texto = st.text_area(
        "Termos de busca (1 por linha)",
        value="\n".join(TERMOS_BUSCA_PADRAO),
        height=140,
    )
    pause = st.number_input("Pausa entre páginas (segundos)", min_value=1.0, value=2.0, step=0.5)
    rodar = st.button("Rodar coleta", type="primary")

if "df_resultados" not in st.session_state:
    st.session_state.df_resultados = pd.DataFrame(
        columns=["Nome do Condomínio", "Cidade", "Endereço Completo", "Latitude", "Longitude"]
    )

if rodar:
    termos = [t.strip() for t in termos_texto.splitlines() if t.strip()]

    if not api_key:
        st.error("Informe a Google API Key para iniciar a coleta.")
    elif not cidades:
        st.error("Selecione ao menos uma cidade.")
    elif not termos:
        st.error("Informe ao menos um termo de busca.")
    else:
        with st.spinner("Buscando condomínios..."):
            crawler = CondoCrawler(api_key=api_key, pause_seconds=float(pause))
            resultados = crawler.buscar(cidades=cidades, termos=termos)
            st.session_state.df_resultados = resultados_para_dataframe(resultados)

        st.success(f"Coleta finalizada: {len(st.session_state.df_resultados)} registros encontrados.")


df = st.session_state.df_resultados

col1, col2 = st.columns([3, 2], gap="large")

with col1:
    st.subheader("Mapa")
    if df.empty:
        st.info("Nenhum dado ainda. Configure na lateral e clique em **Rodar coleta**.")
    else:
        pontos = df[["Latitude", "Longitude"]].dropna()
        if pontos.empty:
            st.warning("Nenhum registro com latitude/longitude válidas para plotar no mapa.")
        else:
            st.map(pontos.rename(columns={"Latitude": "lat", "Longitude": "lon"}), zoom=10)

with col2:
    st.subheader("Resumo")
    st.metric("Total de condomínios", int(len(df)))
    if not df.empty:
        cidades_count = df["Cidade"].nunique()
        st.metric("Cidades com resultados", int(cidades_count))

st.subheader("Tabela de resultados")
st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("Lista de georreferências em CSV")
if df.empty:
    st.info("Quando houver resultados, a lista CSV aparecerá aqui para copiar.")
else:
    csv_texto = dataframe_para_csv(df)
    st.text_area(
        "Copie o conteúdo abaixo (Ctrl+C)",
        value=csv_texto,
        height=220,
    )
    st.download_button(
        label="Baixar CSV",
        data=io.BytesIO(csv_texto.encode("utf-8")),
        file_name="condominios_alto_padrao.csv",
        mime="text/csv",
    )
