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
