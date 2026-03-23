"""Shared test fixtures — synthetic rasters and geometries."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import box

@pytest.fixture
def curitiba_bounds():
    return (-49.40, -25.65, -49.15, -25.33)

@pytest.fixture
def curitiba_geometry(curitiba_bounds):
    return box(*curitiba_bounds)

@pytest.fixture
def synthetic_raster_path(tmp_path):
    """6-band raster (100x100). Left=vegetation, Right=urban."""
    path = tmp_path / "synthetic_landsat.tif"
    height, width = 100, 100
    transform = from_bounds(-49.30, -25.50, -49.20, -25.40, width, height)
    data = np.zeros((6, height, width), dtype=np.float32)
    # Left half: vegetation
    data[0, :, :50] = 500; data[1, :, :50] = 800; data[2, :, :50] = 600
    data[3, :, :50] = 4000; data[4, :, :50] = 1500; data[5, :, :50] = 800
    # Right half: urban
    data[0, :, 50:] = 1200; data[1, :, 50:] = 1100; data[2, :, 50:] = 1500
    data[3, :, 50:] = 1800; data[4, :, 50:] = 2500; data[5, :, 50:] = 2000
    with rasterio.open(path, "w", driver="GTiff", height=height, width=width, count=6, dtype="float32", crs="EPSG:4326", transform=transform) as dst:
        dst.write(data)
    return path

@pytest.fixture
def synthetic_ndvi_path(tmp_path):
    """1-band NDVI (100x100). Left=0.7, Right=0.1."""
    path = tmp_path / "synthetic_ndvi.tif"
    height, width = 100, 100
    transform = from_bounds(-49.30, -25.50, -49.20, -25.40, width, height)
    data = np.zeros((1, height, width), dtype=np.float32)
    data[0, :, :50] = 0.7; data[0, :, 50:] = 0.1
    with rasterio.open(path, "w", driver="GTiff", height=height, width=width, count=1, dtype="float32", crs="EPSG:4326", transform=transform) as dst:
        dst.write(data)
    return path

@pytest.fixture
def synthetic_qa_raster_path(tmp_path):
    """QA_PIXEL raster. Top 20 rows=cloudy."""
    path = tmp_path / "synthetic_qa.tif"
    height, width = 100, 100
    transform = from_bounds(-49.30, -25.50, -49.20, -25.40, width, height)
    data = np.zeros((1, height, width), dtype=np.uint16)
    data[0, :20, :] = 8
    with rasterio.open(path, "w", driver="GTiff", height=height, width=width, count=1, dtype="uint16", crs="EPSG:4326", transform=transform) as dst:
        dst.write(data)
    return path

@pytest.fixture
def small_aoi_geometry():
    return box(-49.28, -25.48, -49.22, -25.42)
