# tests/test_correlation.py
import numpy as np
import pytest
from events.correlation import (
    compute_event_ndvi_impact, compute_category_correlation,
)


class TestEventNDVIImpact:
    def test_negative_impact_detected(self):
        """NDVI drops after event → negative impact."""
        ndvi_before = 0.65
        ndvi_after = 0.40
        impact = compute_event_ndvi_impact(ndvi_before, ndvi_after, threshold=0.05)
        assert impact["direction"] == "negativo"
        assert impact["delta"] == pytest.approx(-0.25, abs=0.01)

    def test_positive_impact_detected(self):
        ndvi_before = 0.30
        ndvi_after = 0.55
        impact = compute_event_ndvi_impact(ndvi_before, ndvi_after, threshold=0.05)
        assert impact["direction"] == "positivo"

    def test_neutral_below_threshold(self):
        ndvi_before = 0.50
        ndvi_after = 0.48
        impact = compute_event_ndvi_impact(ndvi_before, ndvi_after, threshold=0.05)
        assert impact["direction"] == "neutro"


class TestCategoryCorrelation:
    def test_returns_per_category_stats(self):
        events = [
            {"categoria": "obra_infraestrutura", "delta_ndvi": -0.15},
            {"categoria": "obra_infraestrutura", "delta_ndvi": -0.20},
            {"categoria": "parque_area_verde", "delta_ndvi": 0.10},
            {"categoria": "parque_area_verde", "delta_ndvi": 0.15},
        ]
        result = compute_category_correlation(events)
        assert result["obra_infraestrutura"]["mean_delta"] < 0
        assert result["parque_area_verde"]["mean_delta"] > 0
