# CwbVerde Plan 1: Pipeline Core — Ingestão, Pré-processamento, NDVI, Features, Export

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data pipeline that ingests satellite imagery from Google Earth Engine, preprocesses it, computes spectral indices (NDVI, NDWI, NDBI, SAVI, EVI) and texture/terrain features, and exports Cloud-Optimized GeoTIFFs ready for the dashboard.

**Architecture:** Modular Python pipeline where each stage (ingest → preprocess → features → export) is an independent, re-runnable module. GEE service account handles authentication. All rasters clip to Curitiba AOI and reproject to SIRGAS 2000 UTM 22S. Outputs are COGs optimized for rio-tiler consumption.

**Tech Stack:** Python 3.10+, earthengine-api, rasterio, geopandas, numpy, scikit-image, pyproj, shapely, pytest

**Spec Reference:** `docs/superpowers/specs/2026-03-23-cwbverde-design.md` — Sections 3 (Modules 1-3), 7, 8, 11

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `pipeline/__init__.py` | Package init |
| Create | `pipeline/config.py` | Constants: years, bands, CRS, paths, thresholds |
| Create | `pipeline/ingest/__init__.py` | Package init |
| Create | `pipeline/ingest/gee_collector.py` | Download Landsat/Sentinel composites from GEE |
| Create | `pipeline/ingest/mapbiomas_loader.py` | Load MapBiomas classification rasters |
| Create | `pipeline/ingest/shapefiles.py` | Load Curitiba/bairros boundaries |
| Create | `pipeline/preprocess/__init__.py` | Package init |
| Create | `pipeline/preprocess/cloud_mask.py` | QA_PIXEL cloud masking |
| Create | `pipeline/preprocess/clip_reproject.py` | Clip to AOI + reproject to EPSG:31982 |
| Create | `pipeline/preprocess/harmonize.py` | Normalize bands across Landsat 5/8/9 sensors |
| Create | `pipeline/features/__init__.py` | Package init |
| Create | `pipeline/features/indices.py` | NDVI, NDWI, NDBI, SAVI, EVI computation |
| Create | `pipeline/features/texture.py` | GLCM contrast + homogeneity |
| Create | `pipeline/features/terrain.py` | SRTM elevation + slope |
| Create | `pipeline/export/__init__.py` | Package init |
| Create | `pipeline/export/cog_writer.py` | Write Cloud-Optimized GeoTIFFs |
| Create | `pipeline/export/parquet_writer.py` | Write stats to Parquet |
| Create | `pipeline/run_pipeline.py` | Orchestrator: run all stages |
| Create | `tests/__init__.py` | Package init |
| Create | `tests/test_config.py` | Test config constants |
| Create | `tests/test_indices.py` | Test spectral index calculations |
| Create | `tests/test_texture.py` | Test GLCM features |
| Create | `tests/test_terrain.py` | Test elevation/slope |
| Create | `tests/test_cloud_mask.py` | Test cloud masking |
| Create | `tests/test_clip_reproject.py` | Test clipping and reprojection |
| Create | `tests/test_harmonize.py` | Test sensor harmonization |
| Create | `tests/test_cog_writer.py` | Test COG output |
| Create | `tests/conftest.py` | Shared fixtures: synthetic rasters, AOI geometry |
| Create | `data/shapefiles/.gitkeep` | Placeholder for shapefiles |
| Create | `pyproject.toml` | Project config |
| Create | `requirements.txt` | Dependencies |
| Create | `.gitignore` | Ignore data/raw, data/processed, etc. |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `pipeline/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/samuelmauli/dev/CwbVerde
git init
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "cwbverde"
version = "0.1.0"
description = "Deforestation mapping system for Curitiba using satellite imagery and ML"
requires-python = ">=3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: Create requirements.txt**

```
# Core geo
rasterio>=1.3
geopandas>=0.14
shapely>=2.0
pyproj>=3.6
numpy>=1.24

# Features
scikit-image>=0.22

# Earth Engine
earthengine-api>=0.1.380

# Data
pandas>=2.0
pyarrow>=14.0

# Export
rio-cogeo>=5.0

# Testing
pytest>=7.4
```

- [ ] **Step 4: Create .gitignore**

```
# Data (large files)
data/raw/
data/processed/
data/features/
data/ndvi/
data/classification/
data/change/
data/mapbiomas/
data/stats/
data/events.db
outputs/
models/

# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Credentials
*.json
!data/shapefiles/*.json
```

- [ ] **Step 5: Create package init files**

```python
# pipeline/__init__.py
"""CwbVerde — Deforestation mapping pipeline for Curitiba."""
```

```python
# tests/__init__.py
```

- [ ] **Step 6: Create directory structure**

```bash
mkdir -p pipeline/ingest pipeline/preprocess pipeline/features pipeline/export
mkdir -p tests
mkdir -p data/raw data/processed data/features data/ndvi data/classification data/change data/mapbiomas data/shapefiles data/stats
mkdir -p outputs/maps outputs/animations outputs/reports outputs/cog
mkdir -p models notebooks gee_scripts
touch pipeline/ingest/__init__.py pipeline/preprocess/__init__.py pipeline/features/__init__.py pipeline/export/__init__.py
touch data/shapefiles/.gitkeep
```

- [ ] **Step 7: Install dependencies and verify**

```bash
pip install -r requirements.txt
python -c "import rasterio; import geopandas; import numpy; print('OK')"
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml requirements.txt .gitignore pipeline/ tests/ data/shapefiles/.gitkeep
git commit -m "chore: scaffold CwbVerde project structure"
```

---

## Task 2: Pipeline Config

**Files:**
- Create: `pipeline/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pipeline.config import (
    YEARS, AOI_BOUNDS, TARGET_CRS, PIXEL_SIZE_M,
    LANDSAT5_BANDS, LANDSAT8_BANDS, SENTINEL2_BANDS,
    UNIFIED_BANDS, NDVI_THRESHOLD, CLOUD_COVER_MAX,
    DATA_DIR, OUTPUT_DIR,
)


def test_years_range():
    assert YEARS == list(range(2000, 2025))
    assert len(YEARS) == 25


def test_aoi_bounds_curitiba():
    lon_min, lat_min, lon_max, lat_max = AOI_BOUNDS
    assert -49.5 < lon_min < -49.0
    assert -25.7 < lat_min < -25.2
    assert -49.3 < lon_max < -49.0
    assert -25.4 < lat_max < -25.2


def test_target_crs():
    assert TARGET_CRS == "EPSG:31982"


def test_pixel_size():
    assert PIXEL_SIZE_M == 30


def test_unified_bands():
    assert "blue" in UNIFIED_BANDS
    assert "green" in UNIFIED_BANDS
    assert "red" in UNIFIED_BANDS
    assert "nir" in UNIFIED_BANDS
    assert "swir1" in UNIFIED_BANDS
    assert "swir2" in UNIFIED_BANDS


def test_sensor_band_mappings_have_all_unified():
    for band in UNIFIED_BANDS:
        assert band in LANDSAT5_BANDS, f"Missing {band} in Landsat 5"
        assert band in LANDSAT8_BANDS, f"Missing {band} in Landsat 8"
        assert band in SENTINEL2_BANDS, f"Missing {band} in Sentinel-2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — cannot import from pipeline.config

- [ ] **Step 3: Write implementation**

```python
# pipeline/config.py
"""Pipeline configuration — constants, paths, band mappings."""
from pathlib import Path

# ── Project Paths ──
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"

# ── Temporal Range ──
YEARS = list(range(2000, 2025))  # 2000 through 2024

# ── Area of Interest: Curitiba bounding box [lon_min, lat_min, lon_max, lat_max] ──
AOI_BOUNDS = (-49.40, -25.65, -49.15, -25.33)

# ── Coordinate Reference System ──
TARGET_CRS = "EPSG:31982"  # SIRGAS 2000 UTM Zone 22S

# ── Pixel Size ──
PIXEL_SIZE_M = 30  # Landsat resolution in meters
PIXEL_AREA_HA = (PIXEL_SIZE_M ** 2) / 10_000  # 0.09 hectares

# ── Cloud Cover ──
CLOUD_COVER_MAX = 20  # percent

# ── NDVI ──
NDVI_THRESHOLD = 0.15  # minimum delta for change detection

# ── Unified Band Names ──
UNIFIED_BANDS = ["blue", "green", "red", "nir", "swir1", "swir2"]

# ── Sensor Band Mappings (GEE band name → unified name) ──
LANDSAT5_BANDS = {
    "blue": "SR_B1",
    "green": "SR_B2",
    "red": "SR_B3",
    "nir": "SR_B4",
    "swir1": "SR_B5",
    "swir2": "SR_B7",
}

LANDSAT8_BANDS = {
    "blue": "SR_B2",
    "green": "SR_B3",
    "red": "SR_B4",
    "nir": "SR_B5",
    "swir1": "SR_B6",
    "swir2": "SR_B7",
}

# Landsat 9 uses same band layout as Landsat 8
LANDSAT9_BANDS = LANDSAT8_BANDS.copy()

SENTINEL2_BANDS = {
    "blue": "B2",
    "green": "B3",
    "red": "B4",
    "nir": "B8",
    "swir1": "B11",
    "swir2": "B12",
}

# ── GEE Collection IDs ──
GEE_COLLECTIONS = {
    "landsat5": "LANDSAT/LT05/C02/T1_L2",   # 1984-2012
    "landsat8": "LANDSAT/LC08/C02/T1_L2",    # 2013-2021
    "landsat9": "LANDSAT/LC09/C02/T1_L2",    # 2021-present
    "sentinel2": "COPERNICUS/S2_SR_HARMONIZED",  # 2015-present
    "srtm": "USGS/SRTMGL1_003",
}

# ── Classification ──
CLASS_NAMES = {
    1: "Floresta",
    2: "Vegetação média",
    3: "Urbano",
    4: "Solo exposto",
    5: "Água",
}

# ── Sensor Selection by Year ──
def get_sensor_for_year(year: int) -> str:
    """Return which sensor to use for a given year."""
    if year <= 2012:
        return "landsat5"
    elif year <= 2020:
        return "landsat8"
    else:
        return "landsat9"


def get_band_mapping(sensor: str) -> dict[str, str]:
    """Return unified→GEE band mapping for a sensor."""
    mappings = {
        "landsat5": LANDSAT5_BANDS,
        "landsat8": LANDSAT8_BANDS,
        "landsat9": LANDSAT9_BANDS,
        "sentinel2": SENTINEL2_BANDS,
    }
    return mappings[sensor]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/config.py tests/test_config.py
git commit -m "feat: add pipeline config with band mappings and constants"
```

---

## Task 3: Test Fixtures (Shared Synthetic Data)

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write conftest with synthetic raster fixtures**

```python
# tests/conftest.py
"""Shared test fixtures — synthetic rasters and geometries."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import box


@pytest.fixture
def curitiba_bounds():
    """Bounding box for Curitiba AOI."""
    return (-49.40, -25.65, -49.15, -25.33)


@pytest.fixture
def curitiba_geometry(curitiba_bounds):
    """Shapely geometry for Curitiba AOI."""
    return box(*curitiba_bounds)


@pytest.fixture
def synthetic_raster_path(tmp_path):
    """Create a synthetic 6-band raster (100x100) simulating Landsat data.

    Band order: blue, green, red, nir, swir1, swir2
    Values are Surface Reflectance scaled (0-10000).
    Includes a vegetation zone (high NIR) and urban zone (low NIR).
    """
    path = tmp_path / "synthetic_landsat.tif"
    height, width = 100, 100
    transform = from_bounds(-49.30, -25.50, -49.20, -25.40, width, height)

    # Create 6 bands
    data = np.zeros((6, height, width), dtype=np.float32)

    # Left half: vegetation (high NIR, low red)
    data[0, :, :50] = 500    # blue
    data[1, :, :50] = 800    # green
    data[2, :, :50] = 600    # red
    data[3, :, :50] = 4000   # nir (high)
    data[4, :, :50] = 1500   # swir1
    data[5, :, :50] = 800    # swir2

    # Right half: urban (low NIR, high red)
    data[0, :, 50:] = 1200   # blue
    data[1, :, 50:] = 1100   # green
    data[2, :, 50:] = 1500   # red
    data[3, :, 50:] = 1800   # nir (low)
    data[4, :, 50:] = 2500   # swir1
    data[5, :, 50:] = 2000   # swir2

    with rasterio.open(
        path, "w", driver="GTiff",
        height=height, width=width, count=6,
        dtype="float32", crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)

    return path


@pytest.fixture
def synthetic_ndvi_path(tmp_path):
    """Create a synthetic 1-band NDVI raster (100x100).

    Left half: high NDVI (0.7) — vegetation
    Right half: low NDVI (0.1) — urban
    """
    path = tmp_path / "synthetic_ndvi.tif"
    height, width = 100, 100
    transform = from_bounds(-49.30, -25.50, -49.20, -25.40, width, height)

    data = np.zeros((1, height, width), dtype=np.float32)
    data[0, :, :50] = 0.7   # vegetation
    data[0, :, 50:] = 0.1   # urban

    with rasterio.open(
        path, "w", driver="GTiff",
        height=height, width=width, count=1,
        dtype="float32", crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)

    return path


@pytest.fixture
def synthetic_qa_raster_path(tmp_path):
    """Create a synthetic QA_PIXEL raster with some cloudy pixels.

    Landsat QA_PIXEL bit 3 = cloud (value 8 when set).
    Top 20 rows are cloudy, rest are clear.
    """
    path = tmp_path / "synthetic_qa.tif"
    height, width = 100, 100
    transform = from_bounds(-49.30, -25.50, -49.20, -25.40, width, height)

    data = np.zeros((1, height, width), dtype=np.uint16)
    data[0, :20, :] = 8  # cloud bit set (bit 3)

    with rasterio.open(
        path, "w", driver="GTiff",
        height=height, width=width, count=1,
        dtype="uint16", crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)

    return path


@pytest.fixture
def small_aoi_geometry():
    """Small AOI that fits within the synthetic rasters."""
    return box(-49.28, -25.48, -49.22, -25.42)
```

- [ ] **Step 2: Verify fixtures load**

Run: `pytest tests/conftest.py --collect-only`
Expected: No errors, fixtures collected

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add shared fixtures with synthetic rasters"
```

---

## Task 4: Spectral Indices (NDVI, NDWI, NDBI, SAVI, EVI)

**Files:**
- Create: `pipeline/features/indices.py`
- Create: `tests/test_indices.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_indices.py
import numpy as np
import pytest
from pipeline.features.indices import (
    compute_ndvi, compute_ndwi, compute_ndbi,
    compute_savi, compute_evi, compute_all_indices,
)


class TestNDVI:
    def test_vegetation_high_ndvi(self):
        """High NIR, low RED → NDVI close to 1."""
        nir = np.array([[4000.0]])
        red = np.array([[600.0]])
        result = compute_ndvi(nir, red)
        assert result[0, 0] == pytest.approx(0.739, abs=0.01)

    def test_urban_low_ndvi(self):
        """Similar NIR and RED → NDVI close to 0."""
        nir = np.array([[1800.0]])
        red = np.array([[1500.0]])
        result = compute_ndvi(nir, red)
        assert result[0, 0] == pytest.approx(0.09, abs=0.01)

    def test_division_by_zero(self):
        """Both zero → NDVI = 0 (no crash)."""
        nir = np.array([[0.0]])
        red = np.array([[0.0]])
        result = compute_ndvi(nir, red)
        assert result[0, 0] == 0.0

    def test_output_range(self):
        """NDVI is clipped to [-1, 1]."""
        nir = np.random.uniform(0, 10000, (50, 50))
        red = np.random.uniform(0, 10000, (50, 50))
        result = compute_ndvi(nir, red)
        assert result.min() >= -1.0
        assert result.max() <= 1.0


class TestNDWI:
    def test_water_high_ndwi(self):
        """High GREEN, low NIR → positive NDWI (water)."""
        green = np.array([[3000.0]])
        nir = np.array([[500.0]])
        result = compute_ndwi(green, nir)
        assert result[0, 0] > 0.5

    def test_vegetation_negative_ndwi(self):
        """Low GREEN, high NIR → negative NDWI."""
        green = np.array([[800.0]])
        nir = np.array([[4000.0]])
        result = compute_ndwi(green, nir)
        assert result[0, 0] < 0


class TestNDBI:
    def test_urban_positive_ndbi(self):
        """High SWIR, low NIR → positive NDBI (built-up)."""
        swir = np.array([[3000.0]])
        nir = np.array([[1500.0]])
        result = compute_ndbi(swir, nir)
        assert result[0, 0] > 0

    def test_vegetation_negative_ndbi(self):
        """Low SWIR, high NIR → negative NDBI."""
        swir = np.array([[800.0]])
        nir = np.array([[4000.0]])
        result = compute_ndbi(swir, nir)
        assert result[0, 0] < 0


class TestSAVI:
    def test_savi_vegetation(self):
        """Vegetation pixels → SAVI > 0.4."""
        nir = np.array([[4000.0]])
        red = np.array([[600.0]])
        result = compute_savi(nir, red, L=0.5)
        assert result[0, 0] > 0.4

    def test_savi_bare_soil(self):
        """Bare soil → SAVI close to 0."""
        nir = np.array([[1200.0]])
        red = np.array([[1100.0]])
        result = compute_savi(nir, red, L=0.5)
        assert result[0, 0] < 0.1


class TestEVI:
    def test_evi_vegetation(self):
        """Dense vegetation → EVI > 0.3."""
        nir = np.array([[4000.0]])
        red = np.array([[600.0]])
        blue = np.array([[500.0]])
        result = compute_evi(nir, red, blue)
        assert result[0, 0] > 0.3

    def test_evi_clipped(self):
        """EVI stays in reasonable range [-1, 1]."""
        nir = np.random.uniform(0, 10000, (50, 50))
        red = np.random.uniform(0, 10000, (50, 50))
        blue = np.random.uniform(0, 10000, (50, 50))
        result = compute_evi(nir, red, blue)
        assert result.min() >= -1.0
        assert result.max() <= 1.0


class TestComputeAllIndices:
    def test_returns_dict_with_all_indices(self, synthetic_raster_path):
        """compute_all_indices returns dict with all 5 index arrays."""
        import rasterio
        with rasterio.open(synthetic_raster_path) as src:
            bands = {
                "blue": src.read(1),
                "green": src.read(2),
                "red": src.read(3),
                "nir": src.read(4),
                "swir1": src.read(5),
                "swir2": src.read(6),
            }
        result = compute_all_indices(bands)
        assert set(result.keys()) == {"ndvi", "ndwi", "ndbi", "savi", "evi"}
        for name, arr in result.items():
            assert arr.shape == (100, 100), f"{name} wrong shape"

    def test_vegetation_zone_high_ndvi(self, synthetic_raster_path):
        """Left half of synthetic raster (vegetation) has NDVI > 0.5."""
        import rasterio
        with rasterio.open(synthetic_raster_path) as src:
            bands = {
                "blue": src.read(1), "green": src.read(2),
                "red": src.read(3), "nir": src.read(4),
                "swir1": src.read(5), "swir2": src.read(6),
            }
        result = compute_all_indices(bands)
        veg_zone_ndvi = result["ndvi"][:, :50].mean()
        assert veg_zone_ndvi > 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_indices.py -v`
Expected: FAIL — cannot import

- [ ] **Step 3: Write implementation**

```python
# pipeline/features/indices.py
"""Spectral index computation — NDVI, NDWI, NDBI, SAVI, EVI."""
import numpy as np


def _safe_normalized_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute (a - b) / (a + b), handling division by zero."""
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            (a + b) == 0,
            0.0,
            (a - b) / (a + b),
        )
    return np.clip(result.astype(np.float32), -1.0, 1.0)


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalized Difference Vegetation Index.

    NDVI = (NIR - RED) / (NIR + RED)
    High values (>0.4) indicate vegetation.
    """
    return _safe_normalized_diff(nir, red)


def compute_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalized Difference Water Index (McFeeters).

    NDWI = (GREEN - NIR) / (GREEN + NIR)
    Positive values indicate water bodies.
    """
    return _safe_normalized_diff(green, nir)


def compute_ndbi(swir: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalized Difference Built-up Index.

    NDBI = (SWIR - NIR) / (SWIR + NIR)
    Positive values indicate built-up/urban areas.
    """
    return _safe_normalized_diff(swir, nir)


def compute_savi(nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray:
    """Soil-Adjusted Vegetation Index.

    SAVI = ((NIR - RED) / (NIR + RED + L)) * (1 + L)
    Better than NDVI for areas with exposed soil.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            (nir + red + L) == 0,
            0.0,
            ((nir - red) / (nir + red + L)) * (1 + L),
        )
    return np.clip(result.astype(np.float32), -1.0, 1.0)


def compute_evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray,
                G: float = 2.5, C1: float = 6.0, C2: float = 7.5,
                L_evi: float = 1.0) -> np.ndarray:
    """Enhanced Vegetation Index.

    EVI = G * (NIR - RED) / (NIR + C1*RED - C2*BLUE + L)
    Better for dense vegetation (corrects atmospheric influence).
    """
    denominator = nir + C1 * red - C2 * blue + L_evi
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            denominator == 0,
            0.0,
            G * (nir - red) / denominator,
        )
    return np.clip(result.astype(np.float32), -1.0, 1.0)


def compute_all_indices(bands: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Compute all spectral indices from a dict of named bands.

    Args:
        bands: Dict with keys "blue", "green", "red", "nir", "swir1", "swir2".
               Each value is a 2D numpy array (H, W).

    Returns:
        Dict with keys "ndvi", "ndwi", "ndbi", "savi", "evi".
    """
    return {
        "ndvi": compute_ndvi(bands["nir"], bands["red"]),
        "ndwi": compute_ndwi(bands["green"], bands["nir"]),
        "ndbi": compute_ndbi(bands["swir1"], bands["nir"]),
        "savi": compute_savi(bands["nir"], bands["red"]),
        "evi": compute_evi(bands["nir"], bands["red"], bands["blue"]),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_indices.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/features/indices.py tests/test_indices.py
git commit -m "feat: add spectral indices (NDVI, NDWI, NDBI, SAVI, EVI)"
```

---

## Task 5: GLCM Texture Features

**Files:**
- Create: `pipeline/features/texture.py`
- Create: `tests/test_texture.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_texture.py
import numpy as np
import pytest
from pipeline.features.texture import compute_glcm_features


class TestGLCMFeatures:
    def test_returns_contrast_and_homogeneity(self):
        """Output dict has 'contrast' and 'homogeneity' keys."""
        band = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = compute_glcm_features(band, window_size=5)
        assert "contrast" in result
        assert "homogeneity" in result

    def test_output_shape_matches_input(self):
        """Output arrays have same shape as input."""
        band = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
        result = compute_glcm_features(band, window_size=5)
        assert result["contrast"].shape == (50, 50)
        assert result["homogeneity"].shape == (50, 50)

    def test_uniform_region_low_contrast(self):
        """A uniform region should have very low contrast."""
        band = np.full((30, 30), 128, dtype=np.uint8)
        result = compute_glcm_features(band, window_size=5)
        assert result["contrast"].mean() < 1.0

    def test_uniform_region_high_homogeneity(self):
        """A uniform region should have high homogeneity."""
        band = np.full((30, 30), 128, dtype=np.uint8)
        result = compute_glcm_features(band, window_size=5)
        assert result["homogeneity"].mean() > 0.8

    def test_noisy_region_higher_contrast(self):
        """A random/noisy region has higher contrast than uniform."""
        uniform = np.full((30, 30), 128, dtype=np.uint8)
        noisy = np.random.randint(0, 256, (30, 30), dtype=np.uint8)
        r_uniform = compute_glcm_features(uniform, window_size=5)
        r_noisy = compute_glcm_features(noisy, window_size=5)
        assert r_noisy["contrast"].mean() > r_uniform["contrast"].mean()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_texture.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/features/texture.py
"""GLCM texture features — contrast and homogeneity."""
import numpy as np
from skimage.feature import graycomatrix, graycoprops


def compute_glcm_features(
    band: np.ndarray,
    window_size: int = 5,
    levels: int = 64,
    distances: list[int] | None = None,
    angles: list[float] | None = None,
) -> dict[str, np.ndarray]:
    """Compute GLCM contrast and homogeneity over sliding windows.

    Args:
        band: 2D array, uint8 (0-255). If float, will be quantized.
        window_size: Size of the sliding window (must be odd).
        levels: Number of gray levels for GLCM (default 64 for speed).
        distances: GLCM distances (default [1]).
        angles: GLCM angles in radians (default [0]).

    Returns:
        Dict with "contrast" and "homogeneity" arrays, same shape as input.
    """
    if distances is None:
        distances = [1]
    if angles is None:
        angles = [0]

    # Quantize to fewer levels for speed
    if band.dtype != np.uint8:
        band = np.clip(band, 0, 255).astype(np.uint8)
    band_quantized = (band / 256 * levels).astype(np.uint8)

    h, w = band.shape
    pad = window_size // 2
    contrast = np.zeros((h, w), dtype=np.float32)
    homogeneity = np.zeros((h, w), dtype=np.float32)

    # Pad the image
    padded = np.pad(band_quantized, pad, mode="reflect")

    for i in range(h):
        for j in range(w):
            window = padded[i:i + window_size, j:j + window_size]
            glcm = graycomatrix(
                window, distances=distances, angles=angles,
                levels=levels, symmetric=True, normed=True,
            )
            contrast[i, j] = graycoprops(glcm, "contrast")[0, 0]
            homogeneity[i, j] = graycoprops(glcm, "homogeneity")[0, 0]

    return {"contrast": contrast, "homogeneity": homogeneity}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_texture.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/features/texture.py tests/test_texture.py
git commit -m "feat: add GLCM texture features (contrast, homogeneity)"
```

---

## Task 6: Terrain Features (Elevation + Slope)

**Files:**
- Create: `pipeline/features/terrain.py`
- Create: `tests/test_terrain.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_terrain.py
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from pipeline.features.terrain import compute_slope, load_terrain_features


class TestComputeSlope:
    def test_flat_surface_zero_slope(self):
        """Flat elevation → slope = 0."""
        elevation = np.full((50, 50), 900.0)
        slope = compute_slope(elevation, pixel_size=30.0)
        assert slope.mean() == pytest.approx(0.0, abs=0.01)

    def test_tilted_surface_nonzero_slope(self):
        """Tilted plane → uniform nonzero slope."""
        elevation = np.zeros((50, 50))
        for i in range(50):
            elevation[i, :] = i * 10.0  # 10m rise per pixel
        slope = compute_slope(elevation, pixel_size=30.0)
        # Interior pixels should have consistent slope
        interior = slope[2:-2, 2:-2]
        assert interior.mean() > 10.0  # degrees

    def test_output_shape(self):
        elevation = np.random.uniform(800, 1000, (100, 100))
        slope = compute_slope(elevation, pixel_size=30.0)
        assert slope.shape == (100, 100)

    def test_slope_non_negative(self):
        elevation = np.random.uniform(800, 1000, (50, 50))
        slope = compute_slope(elevation, pixel_size=30.0)
        assert slope.min() >= 0.0


class TestLoadTerrainFeatures:
    def test_returns_elevation_and_slope(self, tmp_path):
        """Returns dict with 'elevation' and 'slope'."""
        # Create a synthetic DEM
        dem_path = tmp_path / "dem.tif"
        h, w = 50, 50
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, w, h)
        data = np.random.uniform(850, 1000, (1, h, w)).astype(np.float32)
        with rasterio.open(
            dem_path, "w", driver="GTiff",
            height=h, width=w, count=1,
            dtype="float32", crs="EPSG:4326", transform=transform,
        ) as dst:
            dst.write(data)

        result = load_terrain_features(str(dem_path), pixel_size=30.0)
        assert "elevation" in result
        assert "slope" in result
        assert result["elevation"].shape == (h, w)
        assert result["slope"].shape == (h, w)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_terrain.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/features/terrain.py
"""Terrain features — elevation and slope from SRTM DEM."""
import numpy as np
import rasterio


def compute_slope(elevation: np.ndarray, pixel_size: float = 30.0) -> np.ndarray:
    """Compute slope in degrees from a DEM array.

    Uses numpy gradient to compute dz/dx and dz/dy, then converts to degrees.

    Args:
        elevation: 2D array of elevation values (meters).
        pixel_size: Ground distance per pixel (meters).

    Returns:
        2D array of slope in degrees.
    """
    dy, dx = np.gradient(elevation, pixel_size)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    return slope_deg.astype(np.float32)


def load_terrain_features(
    dem_path: str, pixel_size: float = 30.0
) -> dict[str, np.ndarray]:
    """Load DEM and compute elevation + slope.

    Args:
        dem_path: Path to DEM GeoTIFF (e.g., SRTM).
        pixel_size: Ground distance per pixel (meters).

    Returns:
        Dict with "elevation" and "slope" arrays.
    """
    with rasterio.open(dem_path) as src:
        elevation = src.read(1).astype(np.float32)

    slope = compute_slope(elevation, pixel_size)
    return {"elevation": elevation, "slope": slope}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_terrain.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/features/terrain.py tests/test_terrain.py
git commit -m "feat: add terrain features (elevation, slope from DEM)"
```

---

## Task 7: Cloud Masking

**Files:**
- Create: `pipeline/preprocess/cloud_mask.py`
- Create: `tests/test_cloud_mask.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cloud_mask.py
import numpy as np
import pytest
import rasterio
from pipeline.preprocess.cloud_mask import (
    create_cloud_mask, apply_cloud_mask,
)


class TestCreateCloudMask:
    def test_clear_pixels_are_false(self):
        """QA=0 (clear) → mask=False (not cloudy)."""
        qa = np.array([[0, 0], [0, 0]], dtype=np.uint16)
        mask = create_cloud_mask(qa)
        assert not mask.any()

    def test_cloud_bit_detected(self):
        """QA bit 3 set (value 8) → mask=True (cloudy)."""
        qa = np.array([[8, 0], [0, 8]], dtype=np.uint16)
        mask = create_cloud_mask(qa)
        assert mask[0, 0] is np.True_
        assert mask[1, 1] is np.True_
        assert not mask[0, 1]

    def test_cloud_shadow_detected(self):
        """QA bit 4 set (value 16) → mask=True."""
        qa = np.array([[16]], dtype=np.uint16)
        mask = create_cloud_mask(qa)
        assert mask[0, 0]

    def test_combined_bits(self):
        """Multiple bits set → still detected."""
        qa = np.array([[24]], dtype=np.uint16)  # bits 3 and 4
        mask = create_cloud_mask(qa)
        assert mask[0, 0]


class TestApplyCloudMask:
    def test_cloudy_pixels_become_nan(self):
        """Masked pixels get NaN, clear pixels unchanged."""
        data = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        mask = np.array([[True, False], [False, True]])
        result = apply_cloud_mask(data, mask)
        assert np.isnan(result[0, 0])
        assert result[0, 1] == 2.0
        assert result[1, 0] == 3.0
        assert np.isnan(result[1, 1])

    def test_original_not_modified(self):
        """Input array is not mutated."""
        data = np.array([[1.0, 2.0]], dtype=np.float32)
        mask = np.array([[True, False]])
        apply_cloud_mask(data, mask)
        assert data[0, 0] == 1.0  # unchanged
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cloud_mask.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/preprocess/cloud_mask.py
"""Cloud masking for Landsat QA_PIXEL band."""
import numpy as np


# Landsat Collection 2 QA_PIXEL bit positions
_CLOUD_BIT = 3       # Cloud
_CLOUD_SHADOW_BIT = 4  # Cloud shadow
_CIRRUS_BIT = 2      # Cirrus (high confidence)


def create_cloud_mask(
    qa_band: np.ndarray,
    mask_cloud: bool = True,
    mask_shadow: bool = True,
    mask_cirrus: bool = True,
) -> np.ndarray:
    """Create boolean mask from Landsat QA_PIXEL band.

    Args:
        qa_band: 2D uint16 array from QA_PIXEL band.
        mask_cloud: Mask cloud pixels (bit 3).
        mask_shadow: Mask cloud shadow pixels (bit 4).
        mask_cirrus: Mask cirrus pixels (bit 2).

    Returns:
        Boolean array — True where pixel should be masked (cloudy).
    """
    mask = np.zeros(qa_band.shape, dtype=bool)
    if mask_cloud:
        mask |= (qa_band & (1 << _CLOUD_BIT)) != 0
    if mask_shadow:
        mask |= (qa_band & (1 << _CLOUD_SHADOW_BIT)) != 0
    if mask_cirrus:
        mask |= (qa_band & (1 << _CIRRUS_BIT)) != 0
    return mask


def apply_cloud_mask(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Apply cloud mask to data array — set masked pixels to NaN.

    Args:
        data: 2D float array.
        mask: Boolean array — True = cloudy.

    Returns:
        Copy of data with masked pixels set to NaN.
    """
    result = data.copy().astype(np.float32)
    result[mask] = np.nan
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cloud_mask.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/preprocess/cloud_mask.py tests/test_cloud_mask.py
git commit -m "feat: add cloud masking from Landsat QA_PIXEL band"
```

---

## Task 8: Clip and Reproject

**Files:**
- Create: `pipeline/preprocess/clip_reproject.py`
- Create: `tests/test_clip_reproject.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_clip_reproject.py
import numpy as np
import pytest
import rasterio
from shapely.geometry import box, mapping
from pipeline.preprocess.clip_reproject import clip_to_aoi, reproject_raster


class TestClipToAoi:
    def test_output_smaller_than_input(self, synthetic_raster_path, small_aoi_geometry, tmp_path):
        """Clipped raster should be smaller than original."""
        output = tmp_path / "clipped.tif"
        clip_to_aoi(str(synthetic_raster_path), small_aoi_geometry, str(output))

        with rasterio.open(synthetic_raster_path) as src_orig:
            orig_pixels = src_orig.width * src_orig.height
        with rasterio.open(output) as src_clip:
            clip_pixels = src_clip.width * src_clip.height

        assert clip_pixels < orig_pixels

    def test_output_has_same_band_count(self, synthetic_raster_path, small_aoi_geometry, tmp_path):
        """Clipped raster preserves band count."""
        output = tmp_path / "clipped.tif"
        clip_to_aoi(str(synthetic_raster_path), small_aoi_geometry, str(output))

        with rasterio.open(output) as src:
            assert src.count == 6

    def test_output_exists(self, synthetic_raster_path, small_aoi_geometry, tmp_path):
        """Output file is created."""
        output = tmp_path / "clipped.tif"
        clip_to_aoi(str(synthetic_raster_path), small_aoi_geometry, str(output))
        assert output.exists()


class TestReprojectRaster:
    def test_output_crs_matches_target(self, synthetic_raster_path, tmp_path):
        """Reprojected raster has the target CRS."""
        output = tmp_path / "reprojected.tif"
        reproject_raster(
            str(synthetic_raster_path), str(output), dst_crs="EPSG:31982"
        )
        with rasterio.open(output) as src:
            assert src.crs.to_epsg() == 31982

    def test_data_preserved(self, synthetic_raster_path, tmp_path):
        """Reprojected raster has non-zero data."""
        output = tmp_path / "reprojected.tif"
        reproject_raster(
            str(synthetic_raster_path), str(output), dst_crs="EPSG:31982"
        )
        with rasterio.open(output) as src:
            data = src.read(1)
            assert data.max() > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_clip_reproject.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/preprocess/clip_reproject.py
"""Clip rasters to AOI and reproject to target CRS."""
import rasterio
from rasterio.mask import mask as rasterio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import mapping


def clip_to_aoi(
    input_path: str,
    aoi_geometry,
    output_path: str,
    nodata: float = 0.0,
) -> None:
    """Clip a raster to an area of interest geometry.

    Args:
        input_path: Path to input GeoTIFF.
        aoi_geometry: Shapely geometry to clip to.
        output_path: Path for clipped output.
        nodata: Nodata value for pixels outside AOI.
    """
    shapes = [mapping(aoi_geometry)]

    with rasterio.open(input_path) as src:
        out_image, out_transform = rasterio_mask(
            src, shapes, crop=True, nodata=nodata
        )
        out_meta = src.meta.copy()
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "nodata": nodata,
        })

    with rasterio.open(output_path, "w", **out_meta) as dst:
        dst.write(out_image)


def reproject_raster(
    input_path: str,
    output_path: str,
    dst_crs: str = "EPSG:31982",
    resampling: Resampling = Resampling.bilinear,
) -> None:
    """Reproject a raster to a target CRS.

    Args:
        input_path: Path to input GeoTIFF.
        output_path: Path for reprojected output.
        dst_crs: Target CRS (default: SIRGAS 2000 UTM 22S).
        resampling: Resampling method.
    """
    with rasterio.open(input_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        meta = src.meta.copy()
        meta.update({
            "crs": dst_crs,
            "transform": transform,
            "width": width,
            "height": height,
        })

        with rasterio.open(output_path, "w", **meta) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=resampling,
                )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_clip_reproject.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/preprocess/clip_reproject.py tests/test_clip_reproject.py
git commit -m "feat: add clip-to-AOI and reproject utilities"
```

---

## Task 9: Sensor Harmonization

**Files:**
- Create: `pipeline/preprocess/harmonize.py`
- Create: `tests/test_harmonize.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_harmonize.py
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from pipeline.preprocess.harmonize import (
    harmonize_bands, get_scaling_coefficients,
)


class TestGetScalingCoefficients:
    def test_landsat5_has_coefficients(self):
        coeffs = get_scaling_coefficients("landsat5")
        assert "scale" in coeffs
        assert "offset" in coeffs

    def test_landsat8_has_coefficients(self):
        coeffs = get_scaling_coefficients("landsat8")
        assert "scale" in coeffs

    def test_unknown_sensor_raises(self):
        with pytest.raises(ValueError, match="Unknown sensor"):
            get_scaling_coefficients("unknown_sensor")


class TestHarmonizeBands:
    def test_output_has_unified_band_names(self, tmp_path):
        """Output raster has 6 bands (unified: blue,green,red,nir,swir1,swir2)."""
        # Create a 6-band Landsat-like raster with raw DN values
        path = tmp_path / "raw_landsat8.tif"
        h, w = 20, 20
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, w, h)
        data = np.random.randint(7000, 12000, (6, h, w)).astype(np.uint16)
        with rasterio.open(
            path, "w", driver="GTiff", height=h, width=w, count=6,
            dtype="uint16", crs="EPSG:4326", transform=transform,
        ) as dst:
            dst.write(data)

        output = tmp_path / "harmonized.tif"
        harmonize_bands(str(path), str(output), sensor="landsat8")

        with rasterio.open(output) as src:
            assert src.count == 6
            result = src.read()
            # Harmonized values should be in reflectance range (0-1 ish)
            assert result.max() < 2.0
            assert result.min() >= -0.5

    def test_output_is_float32(self, tmp_path):
        path = tmp_path / "raw.tif"
        h, w = 10, 10
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, w, h)
        data = np.random.randint(7000, 12000, (6, h, w)).astype(np.uint16)
        with rasterio.open(
            path, "w", driver="GTiff", height=h, width=w, count=6,
            dtype="uint16", crs="EPSG:4326", transform=transform,
        ) as dst:
            dst.write(data)

        output = tmp_path / "harmonized.tif"
        harmonize_bands(str(path), str(output), sensor="landsat8")

        with rasterio.open(output) as src:
            assert src.dtypes[0] == "float32"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_harmonize.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/preprocess/harmonize.py
"""Sensor harmonization — normalize band values across Landsat 5/8/9."""
import numpy as np
import rasterio


# Landsat Collection 2 Level-2 Surface Reflectance scaling factors
_SCALING = {
    "landsat5": {"scale": 0.0000275, "offset": -0.2},
    "landsat8": {"scale": 0.0000275, "offset": -0.2},
    "landsat9": {"scale": 0.0000275, "offset": -0.2},
    "sentinel2": {"scale": 0.0001, "offset": 0.0},
}


def get_scaling_coefficients(sensor: str) -> dict[str, float]:
    """Get scaling coefficients for a sensor.

    Args:
        sensor: One of "landsat5", "landsat8", "landsat9", "sentinel2".

    Returns:
        Dict with "scale" and "offset" keys.

    Raises:
        ValueError: If sensor is unknown.
    """
    if sensor not in _SCALING:
        raise ValueError(
            f"Unknown sensor: {sensor}. Expected one of {list(_SCALING.keys())}"
        )
    return _SCALING[sensor]


def harmonize_bands(
    input_path: str,
    output_path: str,
    sensor: str,
) -> None:
    """Apply scaling to convert raw DN to surface reflectance.

    Applies: reflectance = DN * scale + offset
    Output is float32 in approximate range [0, 1].

    Args:
        input_path: Path to raw GeoTIFF with 6 bands.
        output_path: Path for harmonized output.
        sensor: Sensor name for scaling lookup.
    """
    coeffs = get_scaling_coefficients(sensor)
    scale = coeffs["scale"]
    offset = coeffs["offset"]

    with rasterio.open(input_path) as src:
        meta = src.meta.copy()
        meta.update({"dtype": "float32"})
        data = src.read().astype(np.float32)

    # Apply scaling
    harmonized = data * scale + offset

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(harmonized)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harmonize.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/preprocess/harmonize.py tests/test_harmonize.py
git commit -m "feat: add sensor harmonization (DN to surface reflectance)"
```

---

## Task 10: COG Writer

**Files:**
- Create: `pipeline/export/cog_writer.py`
- Create: `tests/test_cog_writer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cog_writer.py
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from pipeline.export.cog_writer import write_cog


class TestWriteCOG:
    def test_output_is_valid_geotiff(self, tmp_path):
        """Written COG is a valid GeoTIFF."""
        data = np.random.uniform(0, 1, (1, 100, 100)).astype(np.float32)
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 100, 100)
        output = tmp_path / "test.tif"

        write_cog(
            data, str(output),
            crs="EPSG:31982", transform=transform,
        )

        with rasterio.open(output) as src:
            assert src.count == 1
            assert src.crs.to_string() == "EPSG:31982"
            read_data = src.read(1)
            assert read_data.shape == (100, 100)

    def test_multiband_cog(self, tmp_path):
        """COG with multiple bands."""
        data = np.random.uniform(0, 1, (3, 50, 50)).astype(np.float32)
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 50, 50)
        output = tmp_path / "multi.tif"

        write_cog(data, str(output), crs="EPSG:31982", transform=transform)

        with rasterio.open(output) as src:
            assert src.count == 3

    def test_cog_has_overviews(self, tmp_path):
        """COG includes internal overviews for fast rendering."""
        data = np.random.uniform(0, 1, (1, 512, 512)).astype(np.float32)
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 512, 512)
        output = tmp_path / "overview.tif"

        write_cog(data, str(output), crs="EPSG:31982", transform=transform)

        with rasterio.open(output) as src:
            assert len(src.overviews(1)) > 0

    def test_cog_uses_deflate_compression(self, tmp_path):
        """COG uses deflate compression."""
        data = np.random.uniform(0, 1, (1, 100, 100)).astype(np.float32)
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 100, 100)
        output = tmp_path / "compressed.tif"

        write_cog(data, str(output), crs="EPSG:31982", transform=transform)

        with rasterio.open(output) as src:
            assert src.compression == rasterio.enums.Compression.deflate
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cog_writer.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/export/cog_writer.py
"""Write Cloud-Optimized GeoTIFFs (COGs)."""
import numpy as np
import rasterio
from rasterio.transform import Affine


def write_cog(
    data: np.ndarray,
    output_path: str,
    crs: str,
    transform: Affine,
    nodata: float | None = None,
    overview_levels: list[int] | None = None,
) -> None:
    """Write a numpy array as a Cloud-Optimized GeoTIFF.

    Args:
        data: 3D array (bands, height, width) or 2D (height, width).
        output_path: Path for output COG.
        crs: Coordinate reference system string.
        transform: Rasterio affine transform.
        nodata: Nodata value (optional).
        overview_levels: Overview decimation levels (default: auto).
    """
    if data.ndim == 2:
        data = data[np.newaxis, :, :]

    bands, height, width = data.shape

    if overview_levels is None:
        # Auto-compute overview levels based on raster size
        max_dim = max(height, width)
        overview_levels = []
        level = 2
        while max_dim / level >= 64:
            overview_levels.append(level)
            level *= 2

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": bands,
        "dtype": data.dtype,
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    if nodata is not None:
        profile["nodata"] = nodata

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data)
        if overview_levels:
            dst.build_overviews(overview_levels, rasterio.enums.Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cog_writer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/export/cog_writer.py tests/test_cog_writer.py
git commit -m "feat: add COG writer with overviews and compression"
```

---

## Task 11: GEE Collector

**Files:**
- Create: `pipeline/ingest/gee_collector.py`

Note: GEE tests require authentication and network, so this module is tested via integration (notebook) rather than unit tests.

- [ ] **Step 1: Write implementation**

```python
# pipeline/ingest/gee_collector.py
"""Google Earth Engine data collector for Landsat composites."""
import ee
from pathlib import Path
from pipeline.config import (
    AOI_BOUNDS, YEARS, CLOUD_COVER_MAX,
    GEE_COLLECTIONS, get_sensor_for_year, get_band_mapping,
    UNIFIED_BANDS,
)


def initialize_gee(service_account_key: str | None = None) -> None:
    """Initialize Earth Engine with service account or default credentials.

    Args:
        service_account_key: Path to service account JSON key file.
                            If None, uses default credentials.
    """
    if service_account_key:
        credentials = ee.ServiceAccountCredentials(
            "", key_file=service_account_key
        )
        ee.Initialize(credentials)
    else:
        ee.Initialize()


def get_curitiba_aoi() -> ee.Geometry:
    """Return Curitiba bounding box as EE Geometry."""
    lon_min, lat_min, lon_max, lat_max = AOI_BOUNDS
    return ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])


def get_yearly_composite(year: int) -> ee.Image:
    """Get median composite for Curitiba for a given year.

    Uses dry season (June-September) to minimize clouds.
    Automatically selects the correct sensor for the year.

    Args:
        year: Year to collect (2000-2024).

    Returns:
        ee.Image with unified band names.
    """
    sensor = get_sensor_for_year(year)
    collection_id = GEE_COLLECTIONS[sensor]
    band_mapping = get_band_mapping(sensor)
    aoi = get_curitiba_aoi()

    # Select GEE band names
    gee_bands = [band_mapping[b] for b in UNIFIED_BANDS]

    collection = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(f"{year}-06-01", f"{year}-09-30")
        .filter(ee.Filter.lt("CLOUD_COVER", CLOUD_COVER_MAX))
        .select(gee_bands, UNIFIED_BANDS)  # rename to unified
    )

    composite = collection.median().clip(aoi)
    return composite


def get_qa_band(year: int) -> ee.Image:
    """Get QA_PIXEL band for cloud masking."""
    sensor = get_sensor_for_year(year)
    collection_id = GEE_COLLECTIONS[sensor]
    aoi = get_curitiba_aoi()

    collection = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(f"{year}-06-01", f"{year}-09-30")
        .filter(ee.Filter.lt("CLOUD_COVER", CLOUD_COVER_MAX))
        .select(["QA_PIXEL"])
    )

    return collection.median().clip(aoi)


def get_srtm_dem() -> ee.Image:
    """Get SRTM DEM for Curitiba."""
    aoi = get_curitiba_aoi()
    return ee.Image(GEE_COLLECTIONS["srtm"]).clip(aoi)


def export_to_drive(
    image: ee.Image,
    description: str,
    folder: str = "CwbVerde",
    scale: int = 30,
) -> ee.batch.Task:
    """Export an EE image to Google Drive.

    Args:
        image: ee.Image to export.
        description: Task description and filename.
        folder: Google Drive folder name.
        scale: Pixel size in meters.

    Returns:
        Started export task.
    """
    aoi = get_curitiba_aoi()
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        scale=scale,
        region=aoi,
        maxPixels=1e9,
        fileFormat="GeoTIFF",
    )
    task.start()
    return task


def collect_all_years(
    folder: str = "CwbVerde",
    years: list[int] | None = None,
) -> list[ee.batch.Task]:
    """Export composites for all years to Google Drive.

    Args:
        folder: Google Drive folder.
        years: List of years (default: all from config).

    Returns:
        List of started export tasks.
    """
    if years is None:
        years = YEARS

    tasks = []
    for year in years:
        composite = get_yearly_composite(year)
        task = export_to_drive(
            composite,
            description=f"curitiba_{year}",
            folder=folder,
        )
        tasks.append(task)
        print(f"Started export: curitiba_{year}")

    # Also export SRTM DEM
    dem = get_srtm_dem()
    dem_task = export_to_drive(dem, description="curitiba_srtm", folder=folder)
    tasks.append(dem_task)
    print("Started export: curitiba_srtm")

    return tasks
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/ingest/gee_collector.py
git commit -m "feat: add GEE collector for Landsat composites and SRTM"
```

---

## Task 12: MapBiomas Loader

**Files:**
- Create: `pipeline/ingest/mapbiomas_loader.py`

- [ ] **Step 1: Write implementation**

```python
# pipeline/ingest/mapbiomas_loader.py
"""Load and reclassify MapBiomas land cover data."""
import numpy as np
import rasterio
from pipeline.config import CLASS_NAMES


# MapBiomas Collection 8 → CwbVerde 5-class reclassification
# Full mapping: https://mapbiomas.org/codigos-de-legenda
_MAPBIOMAS_RECLASSIFICATION = {
    # Floresta (class 1)
    3: 1,   # Formação Florestal
    4: 1,   # Formação Savânica
    5: 1,   # Mangue
    6: 1,   # Floresta Alagável
    49: 1,  # Restinga Arborizada
    # Vegetação média (class 2)
    11: 2,  # Campo Alagado
    12: 2,  # Formação Campestre
    13: 2,  # Outra Formação não Florestal
    15: 2,  # Pastagem
    32: 2,  # Apicum
    29: 2,  # Afloramento Rochoso
    50: 2,  # Restinga Herbácea
    # Urbano (class 3)
    24: 3,  # Infraestrutura Urbana
    30: 3,  # Mineração
    # Solo exposto (class 4)
    25: 4,  # Outra Área não Vegetada
    23: 4,  # Praia, Duna e Areal
    20: 4,  # Cana
    39: 4,  # Soja
    40: 4,  # Arroz
    41: 4,  # Outras Lavouras Temporárias
    36: 4,  # Lavoura Perene
    46: 4,  # Café
    47: 4,  # Citrus
    35: 4,  # Dendê
    48: 4,  # Outras Lavouras Perenes
    9: 4,   # Silvicultura
    21: 4,  # Mosaico de Usos
    # Água (class 5)
    26: 5,  # Corpo D'Água Natural
    33: 5,  # Rio, Lago e Oceano
    31: 5,  # Aquicultura
    27: 5,  # Não observado → treat as nodata but map to 0
}


def reclassify_mapbiomas(
    input_path: str,
    output_path: str,
) -> None:
    """Reclassify MapBiomas raster from ~30 classes to 5 CwbVerde classes.

    Args:
        input_path: Path to MapBiomas GeoTIFF.
        output_path: Path for reclassified output.
    """
    with rasterio.open(input_path) as src:
        data = src.read(1)
        meta = src.meta.copy()

    reclassified = np.zeros_like(data, dtype=np.uint8)
    for mapbiomas_class, cwb_class in _MAPBIOMAS_RECLASSIFICATION.items():
        reclassified[data == mapbiomas_class] = cwb_class

    meta.update({"dtype": "uint8", "count": 1})
    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(reclassified, 1)


def get_class_name(class_id: int) -> str:
    """Return human-readable class name."""
    return CLASS_NAMES.get(class_id, "Desconhecido")
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/ingest/mapbiomas_loader.py
git commit -m "feat: add MapBiomas loader with reclassification to 5 classes"
```

---

## Task 13: Shapefile Loader

**Files:**
- Create: `pipeline/ingest/shapefiles.py`

- [ ] **Step 1: Write implementation**

```python
# pipeline/ingest/shapefiles.py
"""Load Curitiba boundary and bairros shapefiles."""
import geopandas as gpd
from shapely.geometry import box
from pipeline.config import AOI_BOUNDS, TARGET_CRS


def load_curitiba_boundary(shapefile_path: str | None = None) -> gpd.GeoDataFrame:
    """Load Curitiba municipal boundary.

    If no shapefile is provided, creates a bounding box from config.

    Args:
        shapefile_path: Path to Curitiba boundary shapefile.

    Returns:
        GeoDataFrame with Curitiba geometry in EPSG:4326.
    """
    if shapefile_path:
        gdf = gpd.read_file(shapefile_path)
        return gdf.to_crs("EPSG:4326")

    # Fallback: use bounding box from config
    geometry = box(*AOI_BOUNDS)
    return gpd.GeoDataFrame(
        {"name": ["Curitiba"]},
        geometry=[geometry],
        crs="EPSG:4326",
    )


def load_bairros(shapefile_path: str) -> gpd.GeoDataFrame:
    """Load Curitiba bairros (neighborhoods) shapefile.

    Args:
        shapefile_path: Path to bairros shapefile.

    Returns:
        GeoDataFrame with bairro geometries, reprojected to EPSG:4326.
    """
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs("EPSG:4326")
    return gdf


def get_aoi_geometry():
    """Return Curitiba AOI as shapely geometry."""
    return box(*AOI_BOUNDS)
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/ingest/shapefiles.py
git commit -m "feat: add shapefile loader for Curitiba boundary and bairros"
```

---

## Task 14: Parquet Writer

**Files:**
- Create: `pipeline/export/parquet_writer.py`

- [ ] **Step 1: Write implementation**

```python
# pipeline/export/parquet_writer.py
"""Write statistics to Parquet files."""
import pandas as pd
from pathlib import Path


def write_stats_parquet(
    df: pd.DataFrame,
    output_path: str,
) -> None:
    """Write a DataFrame to Parquet with compression.

    Args:
        df: DataFrame with statistics.
        output_path: Path for output .parquet file.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, engine="pyarrow", compression="snappy")


def read_stats_parquet(path: str) -> pd.DataFrame:
    """Read statistics from a Parquet file."""
    return pd.read_parquet(path, engine="pyarrow")
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/export/parquet_writer.py
git commit -m "feat: add Parquet writer for statistics export"
```

---

## Task 15: Pipeline Orchestrator

**Files:**
- Create: `pipeline/run_pipeline.py`

- [ ] **Step 1: Write implementation**

```python
# pipeline/run_pipeline.py
"""Pipeline orchestrator — runs all stages in sequence."""
import logging
from pathlib import Path

from pipeline.config import (
    YEARS, DATA_DIR, OUTPUT_DIR,
    get_sensor_for_year, PIXEL_SIZE_M,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run_preprocess(year: int) -> Path:
    """Run preprocessing for a single year: harmonize + clip + reproject.

    Expects raw GeoTIFF at data/raw/curitiba_{year}.tif
    Outputs to data/processed/curitiba_{year}.tif
    """
    from pipeline.preprocess.harmonize import harmonize_bands
    from pipeline.preprocess.clip_reproject import clip_to_aoi, reproject_raster
    from pipeline.ingest.shapefiles import get_aoi_geometry

    raw_path = DATA_DIR / "raw" / f"curitiba_{year}.tif"
    harmonized_path = DATA_DIR / "processed" / f"harmonized_{year}.tif"
    clipped_path = DATA_DIR / "processed" / f"clipped_{year}.tif"
    output_path = DATA_DIR / "processed" / f"curitiba_{year}.tif"

    if not raw_path.exists():
        logger.warning(f"Raw file not found: {raw_path}, skipping year {year}")
        return output_path

    # Step 1: Harmonize (DN → reflectance)
    sensor = get_sensor_for_year(year)
    logger.info(f"[{year}] Harmonizing bands ({sensor})...")
    harmonized_path.parent.mkdir(parents=True, exist_ok=True)
    harmonize_bands(str(raw_path), str(harmonized_path), sensor=sensor)

    # Step 2: Clip to Curitiba AOI
    aoi = get_aoi_geometry()
    logger.info(f"[{year}] Clipping to Curitiba AOI...")
    clip_to_aoi(str(harmonized_path), aoi, str(clipped_path))

    # Step 3: Reproject to SIRGAS 2000
    logger.info(f"[{year}] Reprojecting to EPSG:31982...")
    reproject_raster(str(clipped_path), str(output_path))

    # Cleanup intermediates
    harmonized_path.unlink(missing_ok=True)
    clipped_path.unlink(missing_ok=True)

    logger.info(f"[{year}] Preprocessing complete → {output_path}")
    return output_path


def run_features(year: int) -> Path:
    """Compute spectral indices for a single year.

    Reads data/processed/curitiba_{year}.tif
    Outputs NDVI to data/ndvi/ndvi_{year}.tif
    Outputs feature stack to data/features/features_{year}.tif
    """
    import rasterio
    import numpy as np
    from pipeline.features.indices import compute_all_indices
    from pipeline.export.cog_writer import write_cog

    input_path = DATA_DIR / "processed" / f"curitiba_{year}.tif"
    ndvi_path = DATA_DIR / "ndvi" / f"ndvi_{year}.tif"
    features_path = DATA_DIR / "features" / f"features_{year}.tif"

    if not input_path.exists():
        logger.warning(f"Processed file not found: {input_path}, skipping")
        return features_path

    with rasterio.open(input_path) as src:
        bands = {
            "blue": src.read(1),
            "green": src.read(2),
            "red": src.read(3),
            "nir": src.read(4),
            "swir1": src.read(5),
            "swir2": src.read(6),
        }
        transform = src.transform
        crs = src.crs.to_string()

    # Compute indices
    logger.info(f"[{year}] Computing spectral indices...")
    indices = compute_all_indices(bands)

    # Save NDVI separately
    ndvi_path.parent.mkdir(parents=True, exist_ok=True)
    write_cog(indices["ndvi"], str(ndvi_path), crs=crs, transform=transform)
    logger.info(f"[{year}] NDVI saved → {ndvi_path}")

    # Stack all features: 6 bands + 5 indices = 11
    # (Texture and terrain added separately in full pipeline)
    feature_arrays = [
        bands["blue"], bands["green"], bands["red"],
        bands["nir"], bands["swir1"], bands["swir2"],
        indices["ndvi"], indices["ndwi"], indices["ndbi"],
        indices["savi"], indices["evi"],
    ]
    stack = np.stack(feature_arrays, axis=0).astype(np.float32)

    features_path.parent.mkdir(parents=True, exist_ok=True)
    write_cog(stack, str(features_path), crs=crs, transform=transform)
    logger.info(f"[{year}] Feature stack (11 bands) saved → {features_path}")

    return features_path


def run_pipeline(
    years: list[int] | None = None,
    steps: list[str] | None = None,
) -> None:
    """Run the full pipeline for all years.

    Args:
        years: List of years to process (default: all).
        steps: List of steps to run: ["preprocess", "features"].
               Default: all steps.
    """
    if years is None:
        years = YEARS
    if steps is None:
        steps = ["preprocess", "features"]

    logger.info(f"Starting pipeline for {len(years)} years: {years[0]}-{years[-1]}")

    for year in years:
        if "preprocess" in steps:
            run_preprocess(year)
        if "features" in steps:
            run_features(year)

    logger.info("Pipeline complete!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CwbVerde Pipeline")
    parser.add_argument("--years", nargs="+", type=int, default=None)
    parser.add_argument("--steps", nargs="+", default=None)
    args = parser.parse_args()
    run_pipeline(years=args.years, steps=args.steps)
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/run_pipeline.py
git commit -m "feat: add pipeline orchestrator with preprocess and features steps"
```

---

## Task 16: Run All Tests

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass.

- [ ] **Step 2: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address any test failures from full suite run"
```

---

## Summary

After completing all 16 tasks, the pipeline has:

| Module | Status | Tests |
|--------|--------|-------|
| `pipeline/config.py` | Config constants, band mappings | `test_config.py` |
| `pipeline/features/indices.py` | NDVI, NDWI, NDBI, SAVI, EVI | `test_indices.py` |
| `pipeline/features/texture.py` | GLCM contrast + homogeneity | `test_texture.py` |
| `pipeline/features/terrain.py` | Elevation + slope | `test_terrain.py` |
| `pipeline/preprocess/cloud_mask.py` | QA_PIXEL masking | `test_cloud_mask.py` |
| `pipeline/preprocess/clip_reproject.py` | Clip AOI + reproject | `test_clip_reproject.py` |
| `pipeline/preprocess/harmonize.py` | DN → reflectance | `test_harmonize.py` |
| `pipeline/export/cog_writer.py` | COG with overviews | `test_cog_writer.py` |
| `pipeline/export/parquet_writer.py` | Stats to Parquet | — |
| `pipeline/ingest/gee_collector.py` | GEE download | Integration only |
| `pipeline/ingest/mapbiomas_loader.py` | Reclassification | — |
| `pipeline/ingest/shapefiles.py` | Boundary loader | — |
| `pipeline/run_pipeline.py` | Orchestrator | — |

**Next plan:** `2026-03-23-cwbverde-plan-2-classification.md` (Ensemble ML + Change Detection)
