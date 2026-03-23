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
