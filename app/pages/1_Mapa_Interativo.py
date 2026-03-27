import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import json
import numpy as np
import streamlit as st
import folium
from folium.plugins import SideBySideLayers
from streamlit_folium import st_folium
import rasterio
from rasterio.transform import from_bounds
from app.config import DATA_DIR
from app.utils.map_utils import (
    render_classification_png_b64,
    render_satellite_rgb_png_b64,
    render_ndvi_png_b64,
)

st.set_page_config(
    page_title="Mapa — CwbVerde",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
section[data-testid="stSidebar"] > div { padding-top: 1rem; }
[data-testid="stMetric"] { background:#f8f9fa; border-radius:8px; padding:8px 12px; }
#MainMenu, footer { visibility:hidden; }
iframe { width:100% !important; }
.change-row { display:flex; justify-content:space-between; align-items:center;
              padding:6px 10px; margin:3px 0; border-radius:6px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = -49.40, -25.65, -49.15, -25.33
BOUNDS     = [[LAT_MIN, LON_MIN], [LAT_MAX, LON_MAX]]
MAP_CENTER = [-25.490, -49.275]
MAP_ZOOM   = 11

CLASS_INFO = {
    1: ("💧 Água",            "#1565C0"),
    2: ("🌳 Vegetação densa", "#1B5E20"),
    3: ("🌿 Vegetação leve",  "#43A047"),
    4: ("🏙️ Urbano",         "#E53935"),
    5: ("🟤 Solo exposto",    "#F57F17"),
}

# ── Session-state ─────────────────────────────────────────────────
if "map_center" not in st.session_state:
    st.session_state.map_center = MAP_CENTER
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = MAP_ZOOM

# ── Curitiba boundary ─────────────────────────────────────────────
BOUNDARY_PATH = DATA_DIR / "shapefiles" / "curitiba_boundary.geojson"
city_geojson = None
if BOUNDARY_PATH.exists():
    with open(BOUNDARY_PATH) as f:
        city_geojson = json.load(f)

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗺️ CwbVerde")
    st.caption("Mapeamento de cobertura vegetal · Curitiba 2000–2023")
    st.divider()

    available_years = sorted([
        int(p.stem.split("_")[1])
        for p in (DATA_DIR / "raw").glob("composite_*.tif")
    ]) or list(range(2000, 2024))

    year = st.select_slider("📅 Ano", options=available_years, value=available_years[-1])
    sensor = "Landsat 5 TM" if year <= 2012 else ("Landsat 8 OLI" if year <= 2021 else "Landsat 9 OLI-2")
    st.caption(f"Sensor: **{sensor}**")

    if year == 2012:
        st.info("2012: interpolado entre Landsat 5 (2011) e Landsat 8 (2013)")

    st.divider()
    st.markdown("**Modo de visualização**")
    view_mode = st.radio(
        "modo",
        ["🗺️ Análise de camadas", "🔍 Comparar Satélite ↔ Classificação"],
        label_visibility="collapsed",
    )

    st.divider()

    if view_mode == "🗺️ Análise de camadas":
        st.markdown("**Fundo do mapa** (use o botão ⊞ no canto do mapa)")
        st.caption("🗺️ Ruas · 🛰️ Satélite Esri · 🌑 Escuro")

        st.markdown("**Overlays de análise**")
        show_class = st.toggle("🎨 Classificação",  value=True)
        show_sat   = st.toggle("🛰️ Landsat RGB",    value=False,
                               help="Imagem real Landsat do ano selecionado")
        show_ndvi  = st.toggle("🌱 NDVI",           value=False,
                               help="Índice de vegetação")
        if show_class:
            op_class = st.slider("Opacidade classificação", 0.1, 1.0, 0.65, 0.05,
                                 label_visibility="collapsed")
        if show_sat:
            op_sat = st.slider("Opacidade Landsat", 0.1, 1.0, 0.90, 0.05,
                               label_visibility="collapsed")
        if show_ndvi:
            op_ndvi = st.slider("Opacidade NDVI", 0.1, 1.0, 0.65, 0.05,
                                label_visibility="collapsed")
    else:
        show_class = show_sat = show_ndvi = False
        st.markdown(
            '<div style="font-size:.85em;color:#555;padding:4px 0">'
            'Arraste o <b>divisor</b> no mapa para comparar a imagem de satélite '
            '(esquerda) com a classificação (direita).</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("**Legenda**")
    for cid, (label, color) in CLASS_INFO.items():
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
            f'<div style="width:14px;height:14px;border-radius:3px;background:{color};flex-shrink:0"></div>'
            f'<span style="font-size:.85em">{label}</span></div>',
            unsafe_allow_html=True,
        )

# ── Build map ─────────────────────────────────────────────────────
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    tiles=None,          # base tiles added manually below
    prefer_canvas=True,
)

# ── Base tile layers (user-selectable via layer control) ──────────
folium.TileLayer(
    tiles="CartoDB positron",
    name="🗺️ Mapa de ruas",
    control=True,
    show=True,
).add_to(m)

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery",
    name="🛰️ Satélite (Esri)",
    control=True,
    show=False,
).add_to(m)

folium.TileLayer(
    tiles="CartoDB dark_matter",
    name="🌑 Mapa escuro",
    control=True,
    show=False,
).add_to(m)

# Curitiba boundary outline
if city_geojson:
    folium.GeoJson(
        city_geojson,
        name="— Limite de Curitiba",
        style_function=lambda _: {
            "color": "#FFD600", "weight": 2.5,
            "fillColor": "transparent", "fillOpacity": 0,
        },
        tooltip="Curitiba — limite municipal",
    ).add_to(m)

# ─────────────────────────────────────────────────────────────────
# MODE A: Análise de camadas
# ─────────────────────────────────────────────────────────────────
if view_mode == "🗺️ Análise de camadas":

    if show_sat:
        with st.spinner(f"Carregando satélite {year}…"):
            sat_b64 = render_satellite_rgb_png_b64(year)
        if sat_b64:
            folium.raster_layers.ImageOverlay(
                image=f"data:image/png;base64,{sat_b64}",
                bounds=BOUNDS, opacity=op_sat,
                name=f"Satélite RGB {year}", cross_origin=False,
            ).add_to(m)

    if show_ndvi:
        with st.spinner(f"Carregando NDVI {year}…"):
            ndvi_b64 = render_ndvi_png_b64(year)
        if ndvi_b64:
            folium.raster_layers.ImageOverlay(
                image=f"data:image/png;base64,{ndvi_b64}",
                bounds=BOUNDS, opacity=op_ndvi, name=f"NDVI {year}",
            ).add_to(m)

    if show_class:
        cls_path = DATA_DIR / "classification" / f"classification_{year}.tif"
        if cls_path.exists():
            with st.spinner(f"Renderizando classificação {year}…"):
                cls_b64 = render_classification_png_b64(year)
            if cls_b64:
                folium.raster_layers.ImageOverlay(
                    image=f"data:image/png;base64,{cls_b64}",
                    bounds=BOUNDS, opacity=op_class, name=f"Classificação {year}",
                ).add_to(m)
        else:
            st.sidebar.warning(f"Classificação não encontrada para {year}")

    folium.LayerControl(collapsed=False, position="topright").add_to(m)

# ─────────────────────────────────────────────────────────────────
# MODE B: Split-screen comparação Satélite ↔ Classificação
# ─────────────────────────────────────────────────────────────────
else:
    with st.spinner(f"Carregando imagens para comparação {year}…"):
        sat_b64 = render_satellite_rgb_png_b64(year)
        cls_b64 = render_classification_png_b64(year)

    if sat_b64 and cls_b64:
        # Left side: satellite
        left_fg = folium.FeatureGroup(name="🛰️ Satélite RGB")
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{sat_b64}",
            bounds=BOUNDS, opacity=0.95, cross_origin=False,
        ).add_to(left_fg)
        left_fg.add_to(m)

        # Right side: classification
        right_fg = folium.FeatureGroup(name="🎨 Classificação")
        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{cls_b64}",
            bounds=BOUNDS, opacity=0.80,
        ).add_to(right_fg)
        right_fg.add_to(m)

        SideBySideLayers(left_fg, right_fg).add_to(m)
        folium.LayerControl(collapsed=False, position="topright").add_to(m)
    else:
        st.warning("Imagens não disponíveis para este ano.")

# ── Layout: mapa + painel ─────────────────────────────────────────
map_col, stats_col = st.columns([3, 1])

with map_col:
    label = "Satélite ↔ Classificação" if view_mode != "🗺️ Análise de camadas" else sensor
    st.markdown(f"### {year} · {label}")
    map_data = st_folium(
        m, width=None, height=620,
        returned_objects=["center", "zoom"],
        key=f"map_{year}_{view_mode}_{show_class}_{show_sat}_{show_ndvi}",
    )
    if map_data and map_data.get("center"):
        c = map_data["center"]
        if isinstance(c, dict):
            st.session_state.map_center = [c.get("lat", MAP_CENTER[0]),
                                           c.get("lng", MAP_CENTER[1])]
    if map_data and map_data.get("zoom"):
        st.session_state.map_zoom = map_data["zoom"]

# ── Stats panel ───────────────────────────────────────────────────
with stats_col:
    st.markdown("### Cobertura")
    cls_path = DATA_DIR / "classification" / f"classification_{year}.tif"
    if cls_path.exists():
        with rasterio.open(str(cls_path)) as src:
            cls_data = src.read(1)
        valid = cls_data[cls_data > 0]
        total = len(valid)
        if total > 0:
            for cid, (label, color) in CLASS_INFO.items():
                pct = (valid == cid).sum() / total * 100
                ha  = (valid == cid).sum() * 0.09
                st.markdown(
                    f'<div style="margin:6px 0;padding:8px 10px;border-radius:6px;'
                    f'background:{color}18;border-left:4px solid {color}">'
                    f'<div style="font-size:.82em;color:#555">{label}</div>'
                    f'<div style="font-size:1.1em;font-weight:700;color:{color}">{pct:.1f}%</div>'
                    f'<div style="font-size:.78em;color:#888">{ha:,.0f} ha</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Execute o pipeline para gerar classificações.")

    st.divider()
    sat_path = DATA_DIR / "raw" / f"composite_{year}.tif"
    if sat_path.exists():
        with rasterio.open(str(sat_path)) as src:
            nir = src.read(4).astype(float)
            red = src.read(3).astype(float)
        np.seterr(divide="ignore", invalid="ignore")
        ndvi_arr = np.where((nir + red) != 0, (nir - red) / (nir + red), np.nan)
        v = ndvi_arr[np.isfinite(ndvi_arr)]
        st.markdown("### NDVI")
        st.metric("Médio",      f"{np.nanmean(v):.3f}")
        st.metric("Verde >0.3", f"{(v>0.3).mean()*100:.1f}%")
        st.metric("Área verde", f"{(v>0.3).sum()*0.09:,.0f} ha")

# ── Análise de Mudanças ───────────────────────────────────────────
st.divider()
st.markdown("## 🔬 Análise de Mudanças")

# Find previous year
prev_year = None
for y in reversed(available_years):
    if y < year:
        prev_year = y
        break

if prev_year is None:
    st.info("Selecione um ano após 2000 para ver a análise de mudanças.")
else:
    prev_cls_path = DATA_DIR / "classification" / f"classification_{prev_year}.tif"
    curr_cls_path = DATA_DIR / "classification" / f"classification_{year}.tif"

    if prev_cls_path.exists() and curr_cls_path.exists():
        with rasterio.open(str(prev_cls_path)) as src:
            prev_cls = src.read(1).astype(np.int16)
        with rasterio.open(str(curr_cls_path)) as src:
            curr_cls = src.read(1).astype(np.int16)

        # Change masks
        was_veg   = (prev_cls == 2) | (prev_cls == 3)
        now_urban = (curr_cls == 4) | (curr_cls == 5)
        was_urban = (prev_cls == 4) | (prev_cls == 5)
        now_veg   = (curr_cls == 2) | (curr_cls == 3)

        deforested_mask  = was_veg & now_urban
        reforested_mask  = was_urban & now_veg
        deforested_ha    = float(deforested_mask.sum() * 0.09)
        reforested_ha    = float(reforested_mask.sum() * 0.09)
        net_ha           = reforested_ha - deforested_ha

        # ── KPIs
        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric(f"🌳 Reflorestado {prev_year}→{year}", f"+{reforested_ha:,.0f} ha",
                      delta="ganho de vegetação")
        with k2:
            st.metric(f"🪓 Desmatado {prev_year}→{year}", f"-{deforested_ha:,.0f} ha",
                      delta="perda de vegetação", delta_color="inverse")
        with k3:
            sign = "+" if net_ha >= 0 else ""
            color_net = "normal" if net_ha >= 0 else "inverse"
            st.metric("⚖️ Saldo líquido", f"{sign}{net_ha:,.0f} ha", delta_color=color_net)

        st.markdown(f"**Interpretação — {prev_year} → {year}:**")

        # Generate contextual explanation
        total_valid = (prev_cls > 0).sum()
        deforested_pct = deforested_ha / (total_valid * 0.09) * 100
        reforested_pct = reforested_ha / (total_valid * 0.09) * 100

        if net_ha > 500:
            st.success(
                f"✅ Período de **recuperação vegetal** — Curitiba ganhou {net_ha:,.0f} ha líquidos de vegetação. "
                f"A área reflorestada ({reforested_ha:,.0f} ha, {reforested_pct:.2f}% da cidade) superou o desmatamento "
                f"({deforested_ha:,.0f} ha, {deforested_pct:.2f}%). Isso sugere abandono de obras, crescimento de "
                f"vegetação em terrenos urbanos ou implantação de parques."
            )
        elif net_ha < -500:
            st.error(
                f"🚨 Período de **pressão urbana** — Curitiba perdeu {abs(net_ha):,.0f} ha líquidos de vegetação. "
                f"O desmatamento ({deforested_ha:,.0f} ha, {deforested_pct:.2f}%) superou o reflorestamento "
                f"({reforested_ha:,.0f} ha). Causas prováveis: expansão de loteamentos, novas vias, obras de "
                f"infraestrutura ou secas que converteram vegetação em solo exposto."
            )
        else:
            st.info(
                f"⚖️ Período de **equilíbrio dinâmico** — o balanço líquido é de {sign}{net_ha:,.0f} ha. "
                f"Desmatamento ({deforested_ha:,.0f} ha) e reflorestamento ({reforested_ha:,.0f} ha) praticamente "
                f"se compensaram. Isto é típico de cidades com pressão constante mas também com políticas de "
                f"arborização ativa."
            )

        # ── Análise espacial por bairro
        st.markdown(f"#### 📍 Bairros mais afetados ({prev_year}→{year})")

        bairros_path = DATA_DIR / "shapefiles" / "bairros_curitiba.geojson"
        if bairros_path.exists():
            import rasterio.features

            with open(bairros_path) as f:
                bairros_gj = json.load(f)

            h, w = prev_cls.shape
            transform = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, w, h)

            bairro_changes = []
            for feat in bairros_gj["features"]:
                nome = feat["properties"]["NOME"]
                geom = feat["geometry"]
                try:
                    bairro_mask = rasterio.features.geometry_mask(
                        [geom], transform=transform, invert=True, out_shape=(h, w)
                    )
                    d_ha = float((deforested_mask & bairro_mask).sum() * 0.09)
                    r_ha = float((reforested_mask & bairro_mask).sum() * 0.09)
                    if d_ha > 0 or r_ha > 0:
                        bairro_changes.append({
                            "Bairro": nome,
                            "Desmatado (ha)": round(d_ha, 1),
                            "Reflorestado (ha)": round(r_ha, 1),
                            "Saldo (ha)": round(r_ha - d_ha, 1),
                        })
                except Exception:
                    pass

            if bairro_changes:
                import pandas as pd
                df_b = pd.DataFrame(bairro_changes).sort_values("Desmatado (ha)", ascending=False)

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**🪓 Mais desmatados**")
                    top_d = df_b.head(8)[["Bairro", "Desmatado (ha)", "Saldo (ha)"]]
                    for _, row in top_d.iterrows():
                        net = row["Saldo (ha)"]
                        sign_c = "🟢" if net >= 0 else "🔴"
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'padding:5px 8px;margin:2px 0;border-radius:5px;background:#FFF3E0">'
                            f'<span style="font-size:.82em">{sign_c} {row["Bairro"]}</span>'
                            f'<span style="font-size:.82em;font-weight:700;color:#E53935">'
                            f'-{row["Desmatado (ha)"]} ha</span></div>',
                            unsafe_allow_html=True,
                        )

                with col_b:
                    st.markdown("**🌱 Mais reflorestados**")
                    top_r = df_b.sort_values("Reflorestado (ha)", ascending=False).head(8)
                    for _, row in top_r.iterrows():
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;'
                            f'padding:5px 8px;margin:2px 0;border-radius:5px;background:#E8F5E9">'
                            f'<span style="font-size:.82em">🌳 {row["Bairro"]}</span>'
                            f'<span style="font-size:.82em;font-weight:700;color:#2E7D32">'
                            f'+{row["Reflorestado (ha)"]} ha</span></div>',
                            unsafe_allow_html=True,
                        )

                with st.expander("📋 Tabela completa por bairro"):
                    st.dataframe(
                        df_b.sort_values("Saldo (ha)"),
                        use_container_width=True, hide_index=True,
                    )
        else:
            st.info("Shapefile de bairros não encontrado para análise espacial.")

        # ── Histórico de mudanças
        st.markdown("#### 📈 Histórico de desmatamento acumulado")
        hist_data = []
        prev = None
        for y in available_years:
            cp = DATA_DIR / "classification" / f"classification_{y}.tif"
            if not cp.exists():
                continue
            with rasterio.open(str(cp)) as src:
                arr = src.read(1).astype(np.int16)
            if prev is not None:
                wv = (prev[0] == 2) | (prev[0] == 3)
                nu = (arr == 4) | (arr == 5)
                wu = (prev[0] == 4) | (prev[0] == 5)
                nv = (arr == 2) | (arr == 3)
                hist_data.append({
                    "Ano": y,
                    "Desmatado (ha)": round(float((wv & nu).sum() * 0.09), 1),
                    "Reflorestado (ha)": round(float((wu & nv).sum() * 0.09), 1),
                })
            prev = (arr, y)

        if hist_data:
            import pandas as pd
            import plotly.graph_objects as go
            df_h = pd.DataFrame(hist_data)
            df_h["Saldo"] = df_h["Reflorestado (ha)"] - df_h["Desmatado (ha)"]

            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_h["Ano"], y=df_h["Reflorestado (ha)"],
                                 name="Reflorestado", marker_color="#43A047"))
            fig.add_trace(go.Bar(x=df_h["Ano"], y=[-v for v in df_h["Desmatado (ha)"]],
                                 name="Desmatado", marker_color="#E53935"))
            fig.add_trace(go.Scatter(x=df_h["Ano"], y=df_h["Saldo"],
                                     name="Saldo líquido", mode="lines+markers",
                                     line=dict(color="#1565C0", width=2),
                                     marker=dict(size=7)))

            # Highlight selected period
            fig.add_vrect(x0=prev_year - 0.4, x1=year + 0.4,
                         fillcolor="rgba(255,193,7,0.12)", line_width=0)

            fig.update_layout(
                barmode="relative",
                template="plotly_white",
                height=320,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(title="Ano", tickmode="linear", dtick=1),
                yaxis=dict(title="Hectares", zeroline=True, zerolinecolor="#ccc"),
                margin=dict(l=40, r=10, t=40, b=40),
            )
            fig.add_annotation(
                x=(prev_year + year) / 2, y=max(df_h["Reflorestado (ha)"]) * 0.9,
                text=f"Período selecionado", showarrow=False,
                font=dict(size=10, color="#F57F17"),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Classificação não disponível para um dos anos selecionados.")
