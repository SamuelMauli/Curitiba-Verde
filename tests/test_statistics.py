import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import box
from pipeline.analysis.statistics import (
    compute_zonal_stats, compute_yearly_summary,
)


@pytest.fixture
def mock_bairros():
    """Two bairros covering left and right halves."""
    return gpd.GeoDataFrame({
        "nome": ["Bairro A", "Bairro B"],
        "geometry": [
            box(-49.30, -25.50, -49.25, -25.40),  # left
            box(-49.25, -25.50, -49.20, -25.40),  # right
        ]
    }, crs="EPSG:4326")


class TestComputeZonalStats:
    def test_returns_per_bairro_stats(self, mock_bairros):
        ndvi = np.zeros((100, 100), dtype=np.float32)
        ndvi[:, :50] = 0.7   # left half: high NDVI
        ndvi[:, 50:] = 0.2   # right half: low NDVI
        from rasterio.transform import from_bounds
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 100, 100)

        stats = compute_zonal_stats(ndvi, mock_bairros, transform, "EPSG:4326")
        assert len(stats) == 2
        assert stats[0]["nome"] == "Bairro A"
        assert stats[0]["ndvi_mean"] > 0.5
        assert stats[1]["ndvi_mean"] < 0.4


class TestYearlySummary:
    def test_summary_has_year_and_metrics(self):
        ndvi = np.random.uniform(0, 1, (50, 50)).astype(np.float32)
        classification = np.random.randint(1, 6, (50, 50)).astype(np.uint8)
        summary = compute_yearly_summary(ndvi, classification, year=2020)
        assert summary["year"] == 2020
        assert "ndvi_mean" in summary
        assert "green_area_ha" in summary
        assert "class_distribution" in summary
