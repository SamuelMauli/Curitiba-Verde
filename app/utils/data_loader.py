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
