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
