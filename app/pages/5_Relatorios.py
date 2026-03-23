# app/pages/5_Relatorios.py
"""Reports page — generate and export reports."""
import streamlit as st
from app.utils.data_loader import load_yearly_stats, load_ndvi_array
from app.utils.report_generator import generate_area_report_png
from app.config import YEARS

st.set_page_config(page_title="Relatórios", page_icon="📄", layout="wide")
st.title("📄 Relatórios")

report_type = st.selectbox("Tipo de Relatório:", [
    "Relatório Geral Curitiba",
    "Relatório por Ano",
])

if report_type == "Relatório Geral Curitiba":
    stats = load_yearly_stats()
    if not stats.empty:
        csv = stats.to_csv(index=False)
        st.download_button("📥 Baixar CSV completo", csv, "cwbverde_dados.csv", "text/csv")

        st.subheader("Preview dos Dados")
        st.dataframe(stats, use_container_width=True)
    else:
        st.warning("Dados não disponíveis.")

elif report_type == "Relatório por Ano":
    year = st.selectbox("Ano:", YEARS, index=len(YEARS) - 1)
    result = load_ndvi_array(year)
    if result is not None:
        ndvi, meta = result
        stats_data = {"ndvi_mean": float(ndvi[~(ndvi == 0)].mean()),
                      "green_area_ha": float((ndvi > 0.3).sum() * 0.09),
                      "green_percent": float((ndvi > 0.3).sum() / (ndvi > -1).sum() * 100)}

        png_bytes = generate_area_report_png(
            title="Curitiba", ndvi_array=ndvi,
            stats=stats_data, year=year,
        )
        st.image(png_bytes, caption=f"Relatório NDVI {year}")
        st.download_button("📥 Baixar PNG", png_bytes, f"cwbverde_{year}.png", "image/png")
    else:
        st.warning(f"NDVI de {year} não disponível.")
