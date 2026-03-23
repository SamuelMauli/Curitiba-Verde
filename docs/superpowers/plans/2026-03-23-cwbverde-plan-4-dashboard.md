# CwbVerde Plan 4: Dashboard Streamlit — Pages, Charts, Reports

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 6-page Streamlit dashboard that displays NDVI maps, temporal evolution, bairro analysis, event timeline, and report generation — consuming data from Plans 1-3.

**Architecture:** Streamlit multipage app. Each page is a self-contained Python file. Shared utilities in `app/utils/`. Custom CSS for professional look. rio-tiler for COG reading. Plotly for interactive charts.

**Tech Stack:** Streamlit 1.x, Plotly, rio-tiler, rasterio, pandas, geopandas, reportlab, imageio

**Spec Reference:** `docs/superpowers/specs/2026-03-23-cwbverde-design.md` — Sections 6, 11

**Depends on:** Plans 1, 2, 3 (needs COGs, stats Parquet, events DB)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `app/Home.py` | Main page — Visão Geral with summary cards |
| Create | `app/pages/1_Mapa_Interativo.py` | Map page (placeholder until Plan 5) |
| Create | `app/pages/2_Evolucao_Temporal.py` | Time series + event timeline |
| Create | `app/pages/3_Analise_Bairros.py` | Bairro ranking + choropleth |
| Create | `app/pages/4_Eventos_Historia.py` | Event timeline + CRUD |
| Create | `app/pages/5_Relatorios.py` | Report generation + export |
| Create | `app/config.py` | App constants, paths |
| Create | `app/utils/__init__.py` | Utils package |
| Create | `app/utils/data_loader.py` | Load COGs, Parquet, shapefiles |
| Create | `app/utils/charts.py` | Plotly chart builders |
| Create | `app/utils/map_utils.py` | rio-tiler helpers for rendering |
| Create | `app/utils/report_generator.py` | PDF/PNG report generation |
| Create | `app/styles/custom.css` | Custom Streamlit theme |
| Create | `.streamlit/config.toml` | Streamlit config |

---

## Task 1: App Scaffold and Config

**Files:**
- Create: `app/config.py`, `app/utils/__init__.py`, `.streamlit/config.toml`, `app/styles/custom.css`

- [ ] **Step 1: Create Streamlit config**

```toml
# .streamlit/config.toml
[theme]
primaryColor = "#2E7D32"
backgroundColor = "#FAFAFA"
secondaryBackgroundColor = "#E8F5E9"
textColor = "#212121"
font = "sans serif"

[server]
headless = true
port = 8501
```

- [ ] **Step 2: Create app config**

```python
# app/config.py
"""Dashboard configuration constants."""
from pathlib import Path

APP_TITLE = "CwbVerde — Mapeamento de Desmatamento de Curitiba"
APP_ICON = "🌳"

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"

YEARS = list(range(2000, 2025))

LAYER_OPTIONS = {
    "NDVI": "ndvi",
    "Classificação (Ensemble)": "classification",
    "MapBiomas": "mapbiomas",
    "Mudança de Vegetação": "change",
}

CLASS_COLORS = {
    1: "#1B5E20",  # Floresta — dark green
    2: "#66BB6A",  # Vegetação média — light green
    3: "#F44336",  # Urbano — red
    4: "#FF9800",  # Solo exposto — orange
    5: "#2196F3",  # Água — blue
}

CLASS_NAMES = {
    1: "Floresta",
    2: "Vegetação média",
    3: "Urbano",
    4: "Solo exposto",
    5: "Água",
}

NDVI_COLORSCALE = [
    [0.0, "#d73027"],   # -0.2: red (no vegetation)
    [0.25, "#fee08b"],  # 0.0: yellow
    [0.5, "#d9ef8b"],   # 0.3: light green
    [0.75, "#66bd63"],  # 0.5: green
    [1.0, "#1a9850"],   # 0.8: dark green
]
```

- [ ] **Step 3: Create custom CSS**

```css
/* app/styles/custom.css */
.main .block-container {
    padding-top: 1rem;
    max-width: 1200px;
}

.stMetric {
    background-color: #E8F5E9;
    border-radius: 8px;
    padding: 10px;
    border-left: 4px solid #2E7D32;
}

h1 {
    color: #1B5E20;
}

h2 {
    color: #2E7D32;
}

.comparison-panel {
    display: flex;
    gap: 1rem;
}
```

- [ ] **Step 4: Commit**

```bash
git add app/config.py app/utils/__init__.py app/styles/custom.css .streamlit/config.toml
git commit -m "feat: scaffold Streamlit app with config and theme"
```

---

## Task 2: Data Loader Utilities

**Files:**
- Create: `app/utils/data_loader.py`

- [ ] **Step 1: Write data loader**

```python
# app/utils/data_loader.py
"""Load pre-processed data for the dashboard."""
import streamlit as st
import pandas as pd
import geopandas as gpd
import rasterio
import numpy as np
from pathlib import Path
from app.config import DATA_DIR, YEARS


@st.cache_data
def load_yearly_stats() -> pd.DataFrame:
    """Load pre-computed yearly statistics from Parquet."""
    path = DATA_DIR / "stats" / "yearly_summary.parquet"
    if path.exists():
        return pd.read_parquet(path)
    # Return empty DataFrame with expected schema
    return pd.DataFrame(columns=[
        "year", "ndvi_mean", "ndvi_std", "green_area_ha",
        "total_area_ha", "green_percent",
    ])


@st.cache_data
def load_bairro_stats(year: int) -> pd.DataFrame:
    """Load per-bairro statistics for a given year."""
    path = DATA_DIR / "stats" / f"bairros_{year}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data
def load_bairros_geojson() -> gpd.GeoDataFrame | None:
    """Load Curitiba bairros shapefile."""
    shp_dir = DATA_DIR / "shapefiles"
    candidates = list(shp_dir.glob("*bairro*.*"))
    if candidates:
        return gpd.read_file(candidates[0]).to_crs("EPSG:4326")
    return None


@st.cache_data
def load_ndvi_array(year: int) -> tuple[np.ndarray, dict] | None:
    """Load NDVI raster for a given year. Returns (array, metadata)."""
    path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
    if not path.exists():
        return None
    with rasterio.open(path) as src:
        return src.read(1), {
            "transform": src.transform,
            "crs": src.crs.to_string(),
            "bounds": src.bounds,
        }


def get_available_years() -> list[int]:
    """Check which years have data available."""
    ndvi_dir = DATA_DIR / "ndvi"
    if not ndvi_dir.exists():
        return YEARS  # return all, will handle missing in pages
    available = []
    for y in YEARS:
        if (ndvi_dir / f"ndvi_{y}.tif").exists():
            available.append(y)
    return available if available else YEARS
```

- [ ] **Step 2: Commit**

```bash
git add app/utils/data_loader.py
git commit -m "feat: add cached data loaders for dashboard"
```

---

## Task 3: Chart Builders

**Files:**
- Create: `app/utils/charts.py`

- [ ] **Step 1: Write chart utilities**

```python
# app/utils/charts.py
"""Plotly chart builders for the dashboard."""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from app.config import CLASS_COLORS, CLASS_NAMES, NDVI_COLORSCALE


def create_ndvi_timeseries(df: pd.DataFrame, title: str = "Evolução do NDVI") -> go.Figure:
    """Create NDVI time series line chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["year"], y=df["ndvi_mean"],
        mode="lines+markers",
        name="NDVI médio",
        line=dict(color="#2E7D32", width=3),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(46, 125, 50, 0.1)",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Ano",
        yaxis_title="NDVI médio",
        yaxis_range=[0, 1],
        template="plotly_white",
        height=400,
    )
    return fig


def create_green_area_timeseries(df: pd.DataFrame) -> go.Figure:
    """Create green area (hectares) time series."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["year"], y=df["green_area_ha"],
        marker_color="#66BB6A",
        name="Área verde (ha)",
    ))
    fig.update_layout(
        title="Área Verde ao Longo dos Anos",
        xaxis_title="Ano",
        yaxis_title="Hectares",
        template="plotly_white",
        height=350,
    )
    return fig


def create_class_distribution_pie(class_dist: dict, year: int) -> go.Figure:
    """Pie chart of land cover classes for a year."""
    names = list(class_dist.keys())
    values = [v["hectares"] for v in class_dist.values()]
    colors = [CLASS_COLORS.get(i + 1, "#999") for i in range(len(names))]
    fig = go.Figure(data=[go.Pie(
        labels=names, values=values,
        marker_colors=colors,
        hole=0.4,
    )])
    fig.update_layout(
        title=f"Uso do Solo — {year}",
        template="plotly_white",
        height=350,
    )
    return fig


def create_bairro_ranking(df: pd.DataFrame, metric: str = "ndvi_mean") -> go.Figure:
    """Horizontal bar chart ranking bairros by metric."""
    sorted_df = df.sort_values(metric, ascending=True).tail(20)
    fig = go.Figure(go.Bar(
        x=sorted_df[metric],
        y=sorted_df["nome"],
        orientation="h",
        marker_color="#2E7D32",
    ))
    fig.update_layout(
        title=f"Top 20 Bairros — {metric}",
        xaxis_title=metric,
        template="plotly_white",
        height=600,
    )
    return fig


def create_comparison_chart(
    data_a: pd.DataFrame, data_b: pd.DataFrame,
    label_a: str, label_b: str,
) -> go.Figure:
    """Dual line chart comparing two areas over time."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data_a["year"], y=data_a["ndvi_mean"],
        name=label_a, line=dict(color="#2E7D32", width=3),
    ))
    fig.add_trace(go.Scatter(
        x=data_b["year"], y=data_b["ndvi_mean"],
        name=label_b, line=dict(color="#F44336", width=3),
    ))
    fig.update_layout(
        title="Comparação NDVI",
        xaxis_title="Ano", yaxis_title="NDVI médio",
        template="plotly_white", height=400,
    )
    return fig


def create_event_timeline(events: list[dict]) -> go.Figure:
    """Create visual timeline of events with color by category."""
    category_colors = {
        "legislacao": "#1565C0",
        "parque_area_verde": "#2E7D32",
        "obra_infraestrutura": "#F44336",
        "empreendimento": "#FF9800",
        "desastre_ambiental": "#B71C1C",
        "politica_publica": "#7B1FA2",
        "licenciamento": "#FF6F00",
        "transporte": "#00838F",
        "demografico": "#546E7A",
        "educacao_cultura": "#4527A0",
    }
    fig = go.Figure()
    for event in events:
        color = category_colors.get(event.get("categoria", ""), "#999")
        fig.add_trace(go.Scatter(
            x=[event["data"]],
            y=[event.get("categoria", "")],
            mode="markers",
            marker=dict(size=12, color=color),
            text=event["titulo"],
            hovertemplate="%{text}<br>%{x}<extra></extra>",
            showlegend=False,
        ))
    fig.update_layout(
        title="Timeline de Eventos",
        template="plotly_white",
        height=400,
        yaxis_title="Categoria",
    )
    return fig
```

- [ ] **Step 2: Commit**

```bash
git add app/utils/charts.py
git commit -m "feat: add Plotly chart builders for dashboard"
```

---

## Task 4: Home Page (Visão Geral)

**Files:**
- Create: `app/Home.py`

- [ ] **Step 1: Write Home page**

```python
# app/Home.py
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
```

- [ ] **Step 2: Commit**

```bash
git add app/Home.py
git commit -m "feat: add Home page with overview cards and charts"
```

---

## Task 5: Evolução Temporal Page

**Files:**
- Create: `app/pages/2_Evolucao_Temporal.py`

- [ ] **Step 1: Write temporal evolution page**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/pages/2_Evolucao_Temporal.py
git commit -m "feat: add temporal evolution page with NDVI time series and events"
```

---

## Task 6: Análise por Bairros Page

**Files:**
- Create: `app/pages/3_Analise_Bairros.py`

- [ ] **Step 1: Write bairros analysis page**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/pages/3_Analise_Bairros.py
git commit -m "feat: add bairro analysis page with ranking and choropleth"
```

---

## Task 7: Eventos e História Page

**Files:**
- Create: `app/pages/4_Eventos_Historia.py`

- [ ] **Step 1: Write events page with CRUD**

```python
# app/pages/4_Eventos_Historia.py
"""Events and history page — timeline + CRUD."""
import streamlit as st
from events.database import EventsDB
from app.config import DATA_DIR

st.set_page_config(page_title="Eventos e História", page_icon="📜", layout="wide")
st.title("📜 Eventos e História de Curitiba")

db_path = DATA_DIR / "events.db"
db = EventsDB(str(db_path))

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    year_filter = st.selectbox("Ano:", [None] + list(range(2000, 2025)),
                                format_func=lambda x: "Todos" if x is None else str(x))
with col2:
    categories = [
        "legislacao", "parque_area_verde", "obra_infraestrutura",
        "empreendimento", "desastre_ambiental", "politica_publica",
        "licenciamento", "transporte", "demografico", "educacao_cultura",
    ]
    cat_filter = st.selectbox("Categoria:", [None] + categories,
                               format_func=lambda x: "Todas" if x is None else x)
with col3:
    st.metric("Total de Eventos", db.count_events())

# List events
events = db.list_events(year=year_filter, categoria=cat_filter, limit=200)

for event in events:
    impact_emoji = {"positivo": "🟢", "negativo": "🔴", "neutro": "⚪"}.get(
        event.get("impacto_ndvi", "neutro"), "⚪"
    )
    with st.expander(f'{impact_emoji} {event["data"]} — {event["titulo"]}'):
        st.write(f"**Categoria:** {event['categoria']}")
        if event.get("descricao"):
            st.write(event["descricao"])
        if event.get("bairros"):
            st.write(f"**Bairros:** {', '.join(event['bairros'])}")
        if event.get("fonte"):
            st.write(f"**Fonte:** {event['fonte']}")
        st.write(f"**Relevância:** {'⭐' * event.get('relevancia', 1)}")

# CRUD: Add new event
st.divider()
st.subheader("Adicionar Novo Evento")
with st.form("new_event"):
    ne_data = st.date_input("Data")
    ne_titulo = st.text_input("Título")
    ne_categoria = st.selectbox("Categoria", categories)
    ne_descricao = st.text_area("Descrição")
    ne_fonte = st.text_input("Fonte")
    ne_relevancia = st.slider("Relevância", 1, 5, 3)
    submitted = st.form_submit_button("Adicionar")
    if submitted and ne_titulo:
        db.create_event(
            data=str(ne_data), titulo=ne_titulo,
            categoria=ne_categoria, descricao=ne_descricao,
            fonte=ne_fonte, relevancia=ne_relevancia,
        )
        st.success(f"Evento '{ne_titulo}' adicionado!")
        st.rerun()

db.close()
```

- [ ] **Step 2: Commit**

```bash
git add app/pages/4_Eventos_Historia.py
git commit -m "feat: add events page with timeline display and CRUD form"
```

---

## Task 8: Relatórios Page

**Files:**
- Create: `app/pages/5_Relatorios.py`
- Create: `app/utils/report_generator.py`

- [ ] **Step 1: Write report generator**

```python
# app/utils/report_generator.py
"""Generate PDF/PNG reports for areas."""
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import numpy as np


def generate_area_report_png(
    title: str,
    ndvi_array: np.ndarray,
    stats: dict,
    year: int,
) -> bytes:
    """Generate a PNG report image for an area.

    Returns PNG bytes.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # NDVI map
    ax = axes[0]
    im = ax.imshow(ndvi_array, cmap="RdYlGn", vmin=-0.2, vmax=0.8)
    ax.set_title(f"NDVI — {year}", fontsize=14, fontweight="bold")
    ax.axis("off")
    plt.colorbar(im, ax=ax, shrink=0.7, label="NDVI")

    # Stats text
    ax2 = axes[1]
    ax2.axis("off")
    text = f"""
    {title}
    Ano: {year}

    NDVI Médio: {stats.get('ndvi_mean', 'N/A'):.3f}
    Área Verde: {stats.get('green_area_ha', 'N/A'):.1f} ha
    Cobertura: {stats.get('green_percent', 'N/A'):.1f}%
    """
    ax2.text(0.1, 0.5, text, fontsize=14, verticalalignment="center",
             fontfamily="monospace", transform=ax2.transAxes)

    plt.suptitle(f"CwbVerde — Relatório de {title}", fontsize=16, fontweight="bold")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf.getvalue()
```

- [ ] **Step 2: Write reports page**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add app/utils/report_generator.py app/pages/5_Relatorios.py
git commit -m "feat: add reports page with PNG generation and CSV export"
```

---

## Task 9: Map Placeholder Page

**Files:**
- Create: `app/pages/1_Mapa_Interativo.py`

- [ ] **Step 1: Write placeholder (will be replaced by Plan 5)**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/pages/1_Mapa_Interativo.py
git commit -m "feat: add map placeholder page with basic Folium"
```

---

## Task 10: Verify App Runs

- [ ] **Step 1: Install Streamlit deps**

```bash
pip install streamlit streamlit-folium plotly folium
```

- [ ] **Step 2: Run the app**

```bash
cd /Users/samuelmauli/dev/CwbVerde && streamlit run app/Home.py
```

Expected: App launches without errors, shows "Dados ainda não processados" message (no data yet).

- [ ] **Step 3: Commit any fixes**

```bash
git add -A && git commit -m "fix: address any Streamlit app startup issues"
```

---

## Summary

| Page | File | Status |
|------|------|--------|
| Home (Visão Geral) | `app/Home.py` | Summary cards + charts |
| Mapa Interativo | `app/pages/1_*.py` | Folium placeholder (Plan 5 replaces) |
| Evolução Temporal | `app/pages/2_*.py` | NDVI time series + event timeline |
| Análise por Bairros | `app/pages/3_*.py` | Ranking + choropleth |
| Eventos e História | `app/pages/4_*.py` | Timeline + CRUD |
| Relatórios | `app/pages/5_*.py` | PNG reports + CSV export |

**Next plan:** `2026-03-23-cwbverde-plan-5-map-component.md` (React Map Component)
