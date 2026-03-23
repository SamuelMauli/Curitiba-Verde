"""Pipeline configuration — constants, paths, band mappings."""
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"

YEARS = list(range(2000, 2025))
AOI_BOUNDS = (-49.40, -25.65, -49.15, -25.33)
TARGET_CRS = "EPSG:31982"
PIXEL_SIZE_M = 30
PIXEL_AREA_HA = (PIXEL_SIZE_M ** 2) / 10_000
CLOUD_COVER_MAX = 20
NDVI_THRESHOLD = 0.15

UNIFIED_BANDS = ["blue", "green", "red", "nir", "swir1", "swir2"]

LANDSAT5_BANDS = {
    "blue": "SR_B1", "green": "SR_B2", "red": "SR_B3",
    "nir": "SR_B4", "swir1": "SR_B5", "swir2": "SR_B7",
}
LANDSAT8_BANDS = {
    "blue": "SR_B2", "green": "SR_B3", "red": "SR_B4",
    "nir": "SR_B5", "swir1": "SR_B6", "swir2": "SR_B7",
}
LANDSAT9_BANDS = LANDSAT8_BANDS.copy()
SENTINEL2_BANDS = {
    "blue": "B2", "green": "B3", "red": "B4",
    "nir": "B8", "swir1": "B11", "swir2": "B12",
}

GEE_COLLECTIONS = {
    "landsat5": "LANDSAT/LT05/C02/T1_L2",
    "landsat8": "LANDSAT/LC08/C02/T1_L2",
    "landsat9": "LANDSAT/LC09/C02/T1_L2",
    "sentinel2": "COPERNICUS/S2_SR_HARMONIZED",
    "srtm": "USGS/SRTMGL1_003",
}

CLASS_NAMES = {1: "Floresta", 2: "Vegetação média", 3: "Urbano", 4: "Solo exposto", 5: "Água"}

def get_sensor_for_year(year: int) -> str:
    if year <= 2012:
        return "landsat5"
    elif year <= 2020:
        return "landsat8"
    else:
        return "landsat9"

def get_band_mapping(sensor: str) -> dict[str, str]:
    mappings = {
        "landsat5": LANDSAT5_BANDS, "landsat8": LANDSAT8_BANDS,
        "landsat9": LANDSAT9_BANDS, "sentinel2": SENTINEL2_BANDS,
    }
    return mappings[sensor]
