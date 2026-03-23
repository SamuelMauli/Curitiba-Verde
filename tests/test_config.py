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
