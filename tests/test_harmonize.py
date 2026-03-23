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
