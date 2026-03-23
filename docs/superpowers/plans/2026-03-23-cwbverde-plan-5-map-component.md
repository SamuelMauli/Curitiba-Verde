# CwbVerde Plan 5: React Map Component — Custom Leaflet, Polygons, Compare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a custom Streamlit component using React-Leaflet that provides polygon drawing, bairro selection, layer switching, temporal slider with event markers, and split-screen comparison mode.

**Architecture:** React+TypeScript frontend communicating with Streamlit Python backend via streamlit-component-lib. The Python side sends COG-rendered PNGs (via rio-tiler) and GeoJSON data. The React side handles all map interactions and sends selections back to Python.

**Tech Stack:** React 18, TypeScript, Leaflet, react-leaflet, leaflet-draw, streamlit-component-lib, rio-tiler

**Spec Reference:** `docs/superpowers/specs/2026-03-23-cwbverde-design.md` — Sections 5, 11

**Depends on:** Plan 4 (Dashboard structure exists)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `app/components/streamlit_map/__init__.py` | Streamlit component Python bridge |
| Create | `app/components/streamlit_map/frontend/package.json` | Node.js deps |
| Create | `app/components/streamlit_map/frontend/tsconfig.json` | TypeScript config |
| Create | `app/components/streamlit_map/frontend/src/index.tsx` | Entry point |
| Create | `app/components/streamlit_map/frontend/src/MapComponent.tsx` | Main map component |
| Create | `app/components/streamlit_map/frontend/src/layers/NDVILayer.tsx` | NDVI overlay |
| Create | `app/components/streamlit_map/frontend/src/layers/BairrosLayer.tsx` | Bairro boundaries |
| Create | `app/components/streamlit_map/frontend/src/tools/PolygonDraw.tsx` | Polygon drawing tool |
| Create | `app/components/streamlit_map/frontend/src/tools/BairroSelect.tsx` | Bairro click selection |
| Create | `app/components/streamlit_map/frontend/src/tools/CompareMode.tsx` | Split-screen compare |
| Create | `app/components/streamlit_map/frontend/src/widgets/TimeSlider.tsx` | Year slider + events |
| Create | `app/components/streamlit_map/frontend/src/widgets/AreaPopup.tsx` | Stats popup |
| Create | `app/components/streamlit_map/frontend/src/widgets/Legend.tsx` | Dynamic legend |
| Create | `app/components/streamlit_map/frontend/src/utils/geoUtils.ts` | Geometry helpers |
| Create | `app/utils/map_utils.py` | rio-tiler PNG rendering |
| Modify | `app/pages/1_Mapa_Interativo.py` | Replace Folium with custom component |

---

## Task 1: Node.js Project Setup

**Files:**
- Create: `app/components/streamlit_map/frontend/package.json`
- Create: `app/components/streamlit_map/frontend/tsconfig.json`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "cwbverde-map-component",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "leaflet": "^1.9.4",
    "leaflet-draw": "^1.0.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-leaflet": "^4.2.1",
    "streamlit-component-lib": "^2.0.0"
  },
  "devDependencies": {
    "@types/leaflet": "^1.9.8",
    "@types/leaflet-draw": "^1.0.11",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.3.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  },
  "browserslist": [">0.2%", "not dead", "not op_mini all"]
}
```

- [ ] **Step 2: Create tsconfig**

```json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Install deps**

```bash
cd app/components/streamlit_map/frontend && npm install
```

- [ ] **Step 4: Commit**

```bash
git add app/components/streamlit_map/frontend/package.json app/components/streamlit_map/frontend/tsconfig.json
git commit -m "feat: setup React project for custom map component"
```

---

## Task 2: Python Bridge (Streamlit Component)

**Files:**
- Create: `app/components/streamlit_map/__init__.py`

- [ ] **Step 1: Write Python bridge**

```python
# app/components/streamlit_map/__init__.py
"""Custom Streamlit map component — Python bridge."""
import streamlit.components.v1 as components
from pathlib import Path

_RELEASE = False
_component_func = components.declare_component(
    "cwbverde_map",
    path=str(Path(__file__).parent / "frontend" / "build") if _RELEASE
    else str(Path(__file__).parent / "frontend"),
    url="http://localhost:3001" if not _RELEASE else None,
)


def cwbverde_map(
    year: int = 2024,
    layer: str = "ndvi",
    ndvi_image_b64: str = "",
    bairros_geojson: dict = None,
    events: list = None,
    show_bairro_borders: bool = True,
    opacity: float = 0.7,
    compare_mode: bool = False,
    height: int = 700,
    key: str = None,
) -> dict:
    """Render the interactive map component.

    Args:
        year: Currently selected year.
        layer: Active layer ("ndvi", "classification", "mapbiomas", "change").
        ndvi_image_b64: Base64-encoded PNG of the raster overlay.
        bairros_geojson: GeoJSON dict of bairro boundaries.
        events: List of events for the current year.
        show_bairro_borders: Toggle bairro borders.
        opacity: Layer opacity.
        compare_mode: Enable split-screen comparison.
        height: Component height in pixels.
        key: Streamlit component key.

    Returns:
        Dict with user actions:
        - selected_bairro: str | None
        - drawn_polygon: GeoJSON | None
        - viewport: {center, zoom}
        - action: str ("select_bairro", "draw_polygon", "compare", etc.)
    """
    result = _component_func(
        year=year,
        layer=layer,
        ndviImageB64=ndvi_image_b64,
        bairrosGeoJson=bairros_geojson or {},
        events=events or [],
        showBairroBorders=show_bairro_borders,
        opacity=opacity,
        compareMode=compare_mode,
        height=height,
        key=key,
        default={"action": None, "selected_bairro": None, "drawn_polygon": None},
    )
    return result
```

- [ ] **Step 2: Commit**

```bash
git add app/components/streamlit_map/__init__.py
git commit -m "feat: add Streamlit-React bridge for map component"
```

---

## Task 3: Main Map Component (React)

**Files:**
- Create: `app/components/streamlit_map/frontend/src/index.tsx`
- Create: `app/components/streamlit_map/frontend/src/MapComponent.tsx`

- [ ] **Step 1: Write entry point**

```tsx
// app/components/streamlit_map/frontend/src/index.tsx
import React from "react"
import ReactDOM from "react-dom"
import MapComponent from "./MapComponent"

ReactDOM.render(
  <React.StrictMode>
    <MapComponent />
  </React.StrictMode>,
  document.getElementById("root")
)
```

- [ ] **Step 2: Write main map component**

```tsx
// app/components/streamlit_map/frontend/src/MapComponent.tsx
import React, { useEffect, useState } from "react"
import {
  Streamlit,
  withStreamlitConnection,
  ComponentProps,
} from "streamlit-component-lib"
import { MapContainer, TileLayer, ImageOverlay, GeoJSON } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import PolygonDraw from "./tools/PolygonDraw"
import BairroSelect from "./tools/BairroSelect"
import TimeSlider from "./widgets/TimeSlider"
import Legend from "./widgets/Legend"

interface MapArgs {
  year: number
  layer: string
  ndviImageB64: string
  bairrosGeoJson: any
  events: any[]
  showBairroBorders: boolean
  opacity: number
  compareMode: boolean
  height: number
}

const CURITIBA_CENTER: [number, number] = [-25.4284, -49.2733]
const CURITIBA_BOUNDS: [[number, number], [number, number]] = [
  [-25.65, -49.40],
  [-25.33, -49.15],
]

const MapComponent: React.FC<ComponentProps> = ({ args }) => {
  const {
    year, layer, ndviImageB64, bairrosGeoJson,
    events, showBairroBorders, opacity, height,
  } = args as MapArgs

  const [selectedBairro, setSelectedBairro] = useState<string | null>(null)
  const [drawnPolygon, setDrawnPolygon] = useState<any>(null)

  useEffect(() => {
    Streamlit.setFrameHeight(height)
  }, [height])

  const handleBairroClick = (bairroName: string) => {
    setSelectedBairro(bairroName)
    Streamlit.setComponentValue({
      action: "select_bairro",
      selected_bairro: bairroName,
      drawn_polygon: null,
    })
  }

  const handlePolygonDrawn = (geojson: any) => {
    setDrawnPolygon(geojson)
    Streamlit.setComponentValue({
      action: "draw_polygon",
      selected_bairro: null,
      drawn_polygon: geojson,
    })
  }

  return (
    <div style={{ width: "100%", height: `${height}px`, position: "relative" }}>
      <MapContainer
        center={CURITIBA_CENTER}
        zoom={11}
        style={{ width: "100%", height: "100%" }}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        />

        {ndviImageB64 && (
          <ImageOverlay
            url={`data:image/png;base64,${ndviImageB64}`}
            bounds={CURITIBA_BOUNDS}
            opacity={opacity}
          />
        )}

        {showBairroBorders && bairrosGeoJson?.features && (
          <BairroSelect
            geojson={bairrosGeoJson}
            onSelect={handleBairroClick}
            selectedBairro={selectedBairro}
          />
        )}

        <PolygonDraw onPolygonDrawn={handlePolygonDrawn} />
      </MapContainer>

      <Legend layer={layer} />
    </div>
  )
}

export default withStreamlitConnection(MapComponent)
```

- [ ] **Step 3: Commit**

```bash
git add app/components/streamlit_map/frontend/src/index.tsx app/components/streamlit_map/frontend/src/MapComponent.tsx
git commit -m "feat: add main React map component with base layers"
```

---

## Task 4: Polygon Draw Tool

**Files:**
- Create: `app/components/streamlit_map/frontend/src/tools/PolygonDraw.tsx`

- [ ] **Step 1: Write polygon drawing component**

```tsx
// app/components/streamlit_map/frontend/src/tools/PolygonDraw.tsx
import React from "react"
import { FeatureGroup } from "react-leaflet"
import { EditControl } from "react-leaflet-draw"
import "leaflet-draw/dist/leaflet.draw.css"

interface Props {
  onPolygonDrawn: (geojson: any) => void
}

const PolygonDraw: React.FC<Props> = ({ onPolygonDrawn }) => {
  const handleCreated = (e: any) => {
    const layer = e.layer
    const geojson = layer.toGeoJSON()
    onPolygonDrawn(geojson.geometry)
  }

  return (
    <FeatureGroup>
      <EditControl
        position="topright"
        onCreated={handleCreated}
        draw={{
          rectangle: false,
          circle: false,
          circlemarker: false,
          marker: false,
          polyline: false,
          polygon: {
            allowIntersection: false,
            shapeOptions: {
              color: "#2E7D32",
              weight: 3,
              fillColor: "#2E7D32",
              fillOpacity: 0.15,
            },
          },
        }}
        edit={{ remove: true, edit: true }}
      />
    </FeatureGroup>
  )
}

export default PolygonDraw
```

- [ ] **Step 2: Commit**

```bash
git add app/components/streamlit_map/frontend/src/tools/PolygonDraw.tsx
git commit -m "feat: add polygon drawing tool"
```

---

## Task 5: Bairro Selection Tool

**Files:**
- Create: `app/components/streamlit_map/frontend/src/tools/BairroSelect.tsx`

- [ ] **Step 1: Write bairro selection component**

```tsx
// app/components/streamlit_map/frontend/src/tools/BairroSelect.tsx
import React from "react"
import { GeoJSON } from "react-leaflet"
import L from "leaflet"

interface Props {
  geojson: any
  onSelect: (bairroName: string) => void
  selectedBairro: string | null
}

const BairroSelect: React.FC<Props> = ({ geojson, onSelect, selectedBairro }) => {
  const style = (feature: any) => {
    const isSelected = feature?.properties?.NOME === selectedBairro
    return {
      color: isSelected ? "#F44336" : "#2E7D32",
      weight: isSelected ? 3 : 1,
      fillColor: isSelected ? "#F44336" : "transparent",
      fillOpacity: isSelected ? 0.15 : 0,
    }
  }

  const onEachFeature = (feature: any, layer: L.Layer) => {
    const name = feature?.properties?.NOME || "Unknown"
    layer.bindTooltip(name)
    layer.on("click", () => onSelect(name))
  }

  return (
    <GeoJSON
      key={selectedBairro || "none"}
      data={geojson}
      style={style}
      onEachFeature={onEachFeature}
    />
  )
}

export default BairroSelect
```

- [ ] **Step 2: Commit**

```bash
git add app/components/streamlit_map/frontend/src/tools/BairroSelect.tsx
git commit -m "feat: add bairro click selection tool"
```

---

## Task 6: Widgets (Legend, TimeSlider, AreaPopup)

**Files:**
- Create: `app/components/streamlit_map/frontend/src/widgets/Legend.tsx`
- Create: `app/components/streamlit_map/frontend/src/widgets/TimeSlider.tsx`
- Create: `app/components/streamlit_map/frontend/src/widgets/AreaPopup.tsx`

- [ ] **Step 1: Write Legend**

```tsx
// app/components/streamlit_map/frontend/src/widgets/Legend.tsx
import React from "react"

const NDVI_LEGEND = [
  { color: "#d73027", label: "< 0.0 — Sem vegetação" },
  { color: "#fee08b", label: "0.0-0.2 — Solo exposto" },
  { color: "#d9ef8b", label: "0.2-0.4 — Veg. baixa" },
  { color: "#66bd63", label: "0.4-0.6 — Veg. moderada" },
  { color: "#1a9850", label: "> 0.6 — Veg. densa" },
]

const CLASS_LEGEND = [
  { color: "#1B5E20", label: "Floresta" },
  { color: "#66BB6A", label: "Vegetação média" },
  { color: "#F44336", label: "Urbano" },
  { color: "#FF9800", label: "Solo exposto" },
  { color: "#2196F3", label: "Água" },
]

interface Props {
  layer: string
}

const Legend: React.FC<Props> = ({ layer }) => {
  const items = layer === "ndvi" ? NDVI_LEGEND : CLASS_LEGEND

  return (
    <div style={{
      position: "absolute", bottom: 20, right: 20,
      background: "white", padding: "10px 14px",
      borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
      zIndex: 1000, fontSize: 12,
    }}>
      <strong style={{ fontSize: 13 }}>Legenda</strong>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", marginTop: 4 }}>
          <div style={{
            width: 16, height: 16, backgroundColor: item.color,
            borderRadius: 3, marginRight: 8,
          }} />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  )
}

export default Legend
```

- [ ] **Step 2: Write TimeSlider and AreaPopup stubs**

These will be controlled from Streamlit side (st.slider) for now — full React integration in future iteration.

```tsx
// app/components/streamlit_map/frontend/src/widgets/TimeSlider.tsx
import React from "react"
// TimeSlider is handled by Streamlit st.slider for now
// This is a placeholder for future in-map slider
const TimeSlider: React.FC = () => null
export default TimeSlider
```

```tsx
// app/components/streamlit_map/frontend/src/widgets/AreaPopup.tsx
import React from "react"
// AreaPopup will be implemented when stats are available
const AreaPopup: React.FC = () => null
export default AreaPopup
```

- [ ] **Step 3: Commit**

```bash
git add app/components/streamlit_map/frontend/src/widgets/
git commit -m "feat: add map legend, time slider stub, and area popup stub"
```

---

## Task 7: rio-tiler Map Utils (Python side)

**Files:**
- Create: `app/utils/map_utils.py`

- [ ] **Step 1: Write rio-tiler helpers**

```python
# app/utils/map_utils.py
"""Map utilities — rio-tiler COG rendering for Streamlit component."""
import base64
from io import BytesIO
import numpy as np
import streamlit as st
from pathlib import Path

from app.config import DATA_DIR


def render_ndvi_png_b64(year: int, bounds: tuple = None) -> str:
    """Render NDVI COG as base64 PNG for the map overlay.

    Args:
        year: Year to render.
        bounds: Optional (west, south, east, north) to render a subregion.

    Returns:
        Base64-encoded PNG string, or empty string if unavailable.
    """
    try:
        from rio_tiler.io import Reader
    except ImportError:
        return ""

    cog_path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
    if not cog_path.exists():
        return ""

    try:
        with Reader(str(cog_path)) as src:
            if bounds:
                img = src.part(bounds, dst_crs="EPSG:4326", width=512, height=512)
            else:
                img = src.preview(width=512, height=512)

            # Apply NDVI colormap (RdYlGn)
            png_bytes = img.render(
                img_format="PNG",
                colormap=_ndvi_colormap(),
            )
    except Exception:
        return ""

    return base64.b64encode(png_bytes).decode()


def _ndvi_colormap() -> dict:
    """Generate a simple NDVI colormap for rio-tiler.

    Maps NDVI values (-1 to 1, stored as uint8 0-255 after scaling)
    to RGBA colors.
    """
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    cmap = plt.cm.RdYlGn
    colormap = {}
    for i in range(256):
        rgba = cmap(i / 255.0)
        colormap[i] = (
            int(rgba[0] * 255),
            int(rgba[1] * 255),
            int(rgba[2] * 255),
            200,  # semi-transparent
        )
    return colormap
```

- [ ] **Step 2: Commit**

```bash
git add app/utils/map_utils.py
git commit -m "feat: add rio-tiler map rendering utilities"
```

---

## Task 8: Update Map Page to Use Custom Component

**Files:**
- Modify: `app/pages/1_Mapa_Interativo.py`

- [ ] **Step 1: Rewrite map page**

```python
# app/pages/1_Mapa_Interativo.py
"""Interactive map page — uses custom React-Leaflet component."""
import streamlit as st
import json
from app.components.streamlit_map import cwbverde_map
from app.utils.map_utils import render_ndvi_png_b64
from app.utils.data_loader import load_bairros_geojson
from app.config import YEARS, LAYER_OPTIONS
from events.database import EventsDB
from app.config import DATA_DIR

st.set_page_config(page_title="Mapa Interativo", page_icon="🗺️", layout="wide")

# Sidebar controls
with st.sidebar:
    st.header("Controles")
    year = st.slider("Ano", 2000, 2024, 2024)
    layer = st.selectbox("Camada", list(LAYER_OPTIONS.keys()))
    opacity = st.slider("Opacidade", 0.0, 1.0, 0.7)
    show_borders = st.checkbox("Limites de bairros", True)
    compare_mode = st.checkbox("Modo comparação", False)

# Load data
ndvi_b64 = render_ndvi_png_b64(year)
bairros = load_bairros_geojson()
bairros_json = json.loads(bairros.to_json()) if bairros is not None else {}

# Load events for year
events = []
db_path = DATA_DIR / "events.db"
if db_path.exists():
    db = EventsDB(str(db_path))
    events = db.list_events(year=year)
    db.close()

# Render map
result = cwbverde_map(
    year=year,
    layer=LAYER_OPTIONS[layer],
    ndvi_image_b64=ndvi_b64,
    bairros_geojson=bairros_json,
    events=events,
    show_bairro_borders=show_borders,
    opacity=opacity,
    compare_mode=compare_mode,
    height=700,
    key=f"map_{year}_{layer}",
)

# Handle user actions from map
if result and result.get("action"):
    if result["action"] == "select_bairro":
        st.sidebar.success(f'Bairro selecionado: {result["selected_bairro"]}')
    elif result["action"] == "draw_polygon":
        st.sidebar.success("Polígono desenhado! Calculando estatísticas...")
        st.sidebar.json(result["drawn_polygon"])
```

- [ ] **Step 2: Build React component**

```bash
cd app/components/streamlit_map/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add app/pages/1_Mapa_Interativo.py
git commit -m "feat: integrate custom React-Leaflet map component"
```

---

## Task 9: Compare Mode Component

**Files:**
- Create: `app/components/streamlit_map/frontend/src/tools/CompareMode.tsx`

- [ ] **Step 1: Write compare mode (future iteration)**

```tsx
// app/components/streamlit_map/frontend/src/tools/CompareMode.tsx
import React from "react"

interface Props {
  enabled: boolean
  areaA: any
  areaB: any
}

// CompareMode: split-screen comparison
// Full implementation in a future iteration
// Currently, comparison is handled server-side in Streamlit
const CompareMode: React.FC<Props> = ({ enabled }) => {
  if (!enabled) return null
  return (
    <div style={{
      position: "absolute", top: 10, left: "50%",
      transform: "translateX(-50%)",
      background: "white", padding: "8px 16px",
      borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
      zIndex: 1000, fontSize: 14,
    }}>
      Modo Comparação — Selecione 2 áreas
    </div>
  )
}

export default CompareMode
```

- [ ] **Step 2: Commit**

```bash
git add app/components/streamlit_map/frontend/src/tools/CompareMode.tsx
git commit -m "feat: add compare mode component stub"
```

---

## Summary

| Component | File | Status |
|-----------|------|--------|
| Python bridge | `__init__.py` | Full Streamlit↔React communication |
| Main map | `MapComponent.tsx` | Leaflet + overlays + tools |
| Polygon draw | `PolygonDraw.tsx` | Leaflet-draw integration |
| Bairro select | `BairroSelect.tsx` | GeoJSON click selection |
| Legend | `Legend.tsx` | NDVI + classification legends |
| Compare mode | `CompareMode.tsx` | Stub for split-screen |
| rio-tiler utils | `map_utils.py` | COG→PNG rendering |
| Map page | `1_Mapa_Interativo.py` | Full integration |

**Next plan:** `2026-03-23-cwbverde-plan-6-deploy.md` (Deploy to HF Spaces)
