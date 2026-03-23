# tests/test_postprocess.py
import numpy as np
import pytest
from pipeline.classification.postprocess import (
    apply_mode_filter, apply_mmu, apply_water_consistency,
    postprocess_classification,
)


class TestModeFilter:
    def test_isolated_pixel_corrected(self):
        """A single pixel surrounded by class 1 should become class 1."""
        data = np.ones((5, 5), dtype=np.uint8)
        data[2, 2] = 3  # isolated pixel
        result = apply_mode_filter(data, window_size=3)
        assert result[2, 2] == 1

    def test_large_region_preserved(self):
        """A large block of class 2 should remain class 2."""
        data = np.ones((10, 10), dtype=np.uint8)
        data[3:7, 3:7] = 2  # 4x4 block
        result = apply_mode_filter(data, window_size=3)
        assert result[5, 5] == 2

    def test_output_shape(self):
        data = np.random.randint(1, 6, (50, 50), dtype=np.uint8)
        result = apply_mode_filter(data, window_size=3)
        assert result.shape == (50, 50)


class TestMMU:
    def test_small_patch_absorbed(self):
        """A 2-pixel patch (< MMU) gets absorbed by surrounding class."""
        data = np.ones((10, 10), dtype=np.uint8)
        data[4, 4] = 3
        data[4, 5] = 3  # 2-pixel patch
        result = apply_mmu(data, min_pixels=5)
        assert result[4, 4] == 1
        assert result[4, 5] == 1

    def test_large_patch_preserved(self):
        """A 25-pixel patch (>= MMU) stays unchanged."""
        data = np.ones((20, 20), dtype=np.uint8)
        data[5:10, 5:10] = 2  # 25-pixel patch
        result = apply_mmu(data, min_pixels=5)
        assert result[7, 7] == 2


class TestWaterConsistency:
    def test_isolated_water_removed(self):
        """Water pixel far from known water body → reclassified."""
        classification = np.ones((20, 20), dtype=np.uint8)  # all forest
        classification[10, 10] = 5  # isolated water pixel
        water_mask = np.zeros((20, 20), dtype=bool)  # no known water nearby
        result = apply_water_consistency(classification, water_mask, buffer_pixels=3)
        assert result[10, 10] != 5

    def test_water_near_known_body_preserved(self):
        """Water pixel near known water body → stays water."""
        classification = np.ones((20, 20), dtype=np.uint8)
        classification[10, 10] = 5
        water_mask = np.zeros((20, 20), dtype=bool)
        water_mask[10, 11] = True  # known water adjacent
        result = apply_water_consistency(classification, water_mask, buffer_pixels=3)
        assert result[10, 10] == 5
