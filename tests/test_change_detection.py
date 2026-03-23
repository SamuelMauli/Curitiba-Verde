import numpy as np
import pytest
from pipeline.analysis.change_detection import (
    compute_ndvi_change, compute_class_transitions,
    quantify_area_change,
)
from pipeline.config import PIXEL_AREA_HA


class TestNDVIChange:
    def test_loss_detected(self):
        """NDVI decrease → negative change."""
        ndvi_before = np.array([[0.8, 0.7], [0.6, 0.5]])
        ndvi_after = np.array([[0.3, 0.7], [0.6, 0.1]])
        change = compute_ndvi_change(ndvi_before, ndvi_after, threshold=0.15)
        assert change[0, 0] == -1  # loss
        assert change[1, 1] == -1  # loss
        assert change[0, 1] == 0   # no change

    def test_gain_detected(self):
        ndvi_before = np.array([[0.2]])
        ndvi_after = np.array([[0.6]])
        change = compute_ndvi_change(ndvi_before, ndvi_after, threshold=0.15)
        assert change[0, 0] == 1  # gain

    def test_below_threshold_is_stable(self):
        ndvi_before = np.array([[0.5]])
        ndvi_after = np.array([[0.45]])
        change = compute_ndvi_change(ndvi_before, ndvi_after, threshold=0.15)
        assert change[0, 0] == 0  # stable


class TestClassTransitions:
    def test_forest_to_urban(self):
        before = np.array([[1, 1], [1, 1]], dtype=np.uint8)
        after = np.array([[3, 1], [1, 3]], dtype=np.uint8)
        matrix = compute_class_transitions(before, after, n_classes=5)
        assert matrix[0, 2] == 2  # class 1 → class 3: 2 pixels

    def test_no_change(self):
        data = np.ones((5, 5), dtype=np.uint8)
        matrix = compute_class_transitions(data, data, n_classes=5)
        assert matrix[0, 0] == 25  # all stay class 1


class TestQuantifyArea:
    def test_area_calculation(self):
        change = np.zeros((100, 100), dtype=np.int8)
        change[:10, :] = -1  # 1000 pixels lost
        stats = quantify_area_change(change)
        expected_ha = 1000 * PIXEL_AREA_HA
        assert stats["loss_ha"] == pytest.approx(expected_ha, abs=0.1)

    def test_gain_area(self):
        change = np.zeros((50, 50), dtype=np.int8)
        change[:5, :5] = 1  # 25 pixels gained
        stats = quantify_area_change(change)
        expected_ha = 25 * PIXEL_AREA_HA
        assert stats["gain_ha"] == pytest.approx(expected_ha, abs=0.1)
