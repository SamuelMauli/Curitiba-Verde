import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
# app/pages/3_Analise_Bairros.py
"""Bairro analysis page — ranking, choropleth, comparison."""
import streamlit as st
import plotly.express as px
from app.utils.data_loader import load_bairro_stats, load_bairros_geojson
from app.utils.charts import create_bairro_ranking, create_comparison_chart
from app.config import YEARS

st.set_page_config(page_title="Análise por Bairros", page_icon="🏘️", layout="wide")
st.title("🏘️ Análise por Bairros")

year = st.slider("Ano", min_value=2000, max_value=2024, value=2024)
bairro_stats = load_bairro_stats(year)

if bairro_stats.empty:
    st.warning(f"Dados de bairros não disponíveis para {year}.")
    st.stop()

# Metric selector
metric = st.selectbox("Métrica:", [
    "ndvi_mean", "green_area_ha", "total_pixels"
], format_func=lambda x: {
    "ndvi_mean": "NDVI Médio",
    "green_area_ha": "Área Verde (ha)",
    "total_pixels": "Total de Pixels",
}[x])

col1, col2 = st.columns(2)

with col1:
    st.subheader("Ranking de Bairros")
    fig = create_bairro_ranking(bairro_stats, metric)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Mapa Coroplético")
    bairros_gdf = load_bairros_geojson()
    if bairros_gdf is not None:
        merged = bairros_gdf.merge(bairro_stats, left_on="NOME", right_on="nome", how="left")
        fig = px.choropleth_mapbox(
            merged, geojson=merged.geometry.__geo_interface__,
            locations=merged.index, color=metric,
            mapbox_style="carto-positron",
            center={"lat": -25.43, "lon": -49.27}, zoom=10,
            color_continuous_scale="RdYlGn",
            height=600,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Shapefile de bairros não encontrado.")

# Comparison
st.divider()
st.subheader("Comparar Bairros")
available_bairros = bairro_stats["nome"].tolist() if "nome" in bairro_stats.columns else []
if len(available_bairros) >= 2:
    selected = st.multiselect("Selecione 2-3 bairros:", available_bairros, max_selections=3)
    if len(selected) >= 2:
        st.info("Comparação temporal requer dados de múltiplos anos (em desenvolvimento).")
