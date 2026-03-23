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
