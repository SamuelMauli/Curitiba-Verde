import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
# app/pages/1_Mapa_Interativo.py
"""Interactive map page — placeholder for React-Leaflet component (Plan 5)."""
import streamlit as st
import folium
from streamlit_folium import st_folium
from app.config import YEARS

st.set_page_config(page_title="Mapa Interativo", page_icon="🗺️", layout="wide")
st.title("🗺️ Mapa Interativo")

year = st.slider("Ano", min_value=2000, max_value=2024, value=2024)

# Basic Folium map as placeholder
m = folium.Map(location=[-25.4284, -49.2733], zoom_start=11, tiles="CartoDB positron")
folium.Rectangle(
    bounds=[[-25.65, -49.40], [-25.33, -49.15]],
    color="#2E7D32", weight=2, fill=False,
    tooltip="Área de estudo — Curitiba",
).add_to(m)

st_folium(m, width=None, height=600)

st.info(
    "🚧 **Mapa interativo completo em desenvolvimento.**\n\n"
    "O componente React-Leaflet customizado com desenho de polígonos, "
    "seleção de bairros e comparação split-screen será implementado no Plan 5."
)
