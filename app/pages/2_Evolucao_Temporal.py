import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
# app/pages/2_Evolucao_Temporal.py
"""Temporal evolution page — NDVI time series + event timeline."""
import streamlit as st
from app.utils.data_loader import load_yearly_stats, load_bairros_geojson
from app.utils.charts import (
    create_ndvi_timeseries, create_event_timeline,
    create_class_distribution_pie,
)
from events.database import EventsDB
from app.config import DATA_DIR

st.set_page_config(page_title="Evolução Temporal", page_icon="📈", layout="wide")
st.title("📈 Evolução Temporal")

stats = load_yearly_stats()

if stats.empty:
    st.warning("Dados não disponíveis. Execute o pipeline primeiro.")
    st.stop()

# NDVI time series
st.plotly_chart(
    create_ndvi_timeseries(stats, title="NDVI Médio — Curitiba (2000-2024)"),
    use_container_width=True,
)

# Event timeline
st.subheader("Timeline de Eventos")
db_path = DATA_DIR / "events.db"
if db_path.exists():
    db = EventsDB(str(db_path))
    events = db.list_events(limit=500)
    if events:
        # Filter by category
        categories = sorted(set(e["categoria"] for e in events))
        selected_cats = st.multiselect("Filtrar por categoria:", categories, default=categories)
        filtered = [e for e in events if e["categoria"] in selected_cats]
        st.plotly_chart(create_event_timeline(filtered), use_container_width=True)
    db.close()
else:
    st.info("Banco de eventos não encontrado.")

# Data table
st.subheader("Dados Anuais")
st.dataframe(
    stats[["year", "ndvi_mean", "green_area_ha", "green_percent"]].rename(columns={
        "year": "Ano",
        "ndvi_mean": "NDVI Médio",
        "green_area_ha": "Área Verde (ha)",
        "green_percent": "Cobertura (%)",
    }),
    use_container_width=True,
)

# Export
csv = stats.to_csv(index=False)
st.download_button("📥 Exportar CSV", csv, "cwbverde_stats.csv", "text/csv")
