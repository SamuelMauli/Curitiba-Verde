# app/Home.py
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
"""CwbVerde — Home page with overview cards and summary."""
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="CwbVerde — Desmatamento Curitiba",
    page_icon="🌳",
    layout="wide",
)

# Load custom CSS
css_path = Path(__file__).parent / "styles" / "custom.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

from app.config import APP_TITLE, YEARS
from app.utils.data_loader import load_yearly_stats, get_available_years
from app.utils.charts import create_ndvi_timeseries, create_green_area_timeseries

st.title(APP_TITLE)
st.markdown("### Mapeamento da evolução do desmatamento e cobertura vegetal de Curitiba-PR (2000–2024)")

# Load data
stats = load_yearly_stats()

if not stats.empty:
    latest = stats.iloc[-1]
    first = stats.iloc[0]
    delta_pct = ((latest["green_percent"] - first["green_percent"]) / first["green_percent"] * 100) if first["green_percent"] > 0 else 0

    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Área Verde Atual", f'{latest["green_area_ha"]:.0f} ha')
    with col2:
        st.metric("Cobertura Vegetal", f'{latest["green_percent"]:.1f}%')
    with col3:
        st.metric("Variação desde 2000", f'{delta_pct:+.1f}%')
    with col4:
        st.metric("NDVI Médio", f'{latest["ndvi_mean"]:.3f}')

    st.divider()

    # Charts
    col_a, col_b = st.columns(2)
    with col_a:
        fig = create_ndvi_timeseries(stats)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig = create_green_area_timeseries(stats)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info(
        "Dados ainda não processados. Execute o pipeline primeiro:\n\n"
        "```bash\npython -m pipeline.run_pipeline\n```"
    )

st.divider()
st.markdown("**Navegue pelas páginas** no menu lateral para explorar o mapa interativo, análise por bairros, timeline de eventos e gerar relatórios.")
