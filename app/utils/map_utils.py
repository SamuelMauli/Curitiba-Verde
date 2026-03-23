import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
"""Map utilities — rio-tiler COG rendering for Streamlit."""
import base64
from io import BytesIO
import numpy as np
from pathlib import Path
from app.config import DATA_DIR
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")


def render_ndvi_png_b64(year: int) -> str:
    """Render NDVI raster as base64 PNG for map overlay."""
    import rasterio
    cog_path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
    if not cog_path.exists():
        return ""
    try:
        with rasterio.open(str(cog_path)) as src:
            ndvi = src.read(1)
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(ndvi, cmap="RdYlGn", vmin=-0.2, vmax=0.8)
        ax.axis("off")
        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", transparent=True, pad_inches=0)
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def get_ndvi_stats_for_area(year: int, bounds: tuple = None) -> dict:
    """Get NDVI statistics for a given year and optional bounds."""
    import rasterio
    cog_path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
    if not cog_path.exists():
        return {}
    with rasterio.open(str(cog_path)) as src:
        ndvi = src.read(1)
    valid = ndvi[ndvi != 0]
    if len(valid) == 0:
        return {}
    return {
        "ndvi_mean": float(valid.mean()),
        "ndvi_std": float(valid.std()),
        "green_pixels": int((valid > 0.3).sum()),
        "total_pixels": int(len(valid)),
        "green_area_ha": float((valid > 0.3).sum() * 0.09),
    }
