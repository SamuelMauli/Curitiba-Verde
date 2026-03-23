# tests/test_texture.py
import numpy as np
import pytest
from pipeline.features.texture import compute_glcm_features


class TestGLCMFeatures:
    def test_returns_contrast_and_homogeneity(self):
        """Output dict has 'contrast' and 'homogeneity' keys."""
        band = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = compute_glcm_features(band, window_size=5)
        assert "contrast" in result
        assert "homogeneity" in result

    def test_output_shape_matches_input(self):
        """Output arrays have same shape as input."""
        band = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
        result = compute_glcm_features(band, window_size=5)
        assert result["contrast"].shape == (50, 50)
        assert result["homogeneity"].shape == (50, 50)

    def test_uniform_region_low_contrast(self):
        """A uniform region should have very low contrast."""
        band = np.full((30, 30), 128, dtype=np.uint8)
        result = compute_glcm_features(band, window_size=5)
        assert result["contrast"].mean() < 1.0

    def test_uniform_region_high_homogeneity(self):
        """A uniform region should have high homogeneity."""
        band = np.full((30, 30), 128, dtype=np.uint8)
        result = compute_glcm_features(band, window_size=5)
        assert result["homogeneity"].mean() > 0.8

    def test_noisy_region_higher_contrast(self):
        """A random/noisy region has higher contrast than uniform."""
        uniform = np.full((30, 30), 128, dtype=np.uint8)
        noisy = np.random.randint(0, 256, (30, 30), dtype=np.uint8)
        r_uniform = compute_glcm_features(uniform, window_size=5)
        r_noisy = compute_glcm_features(noisy, window_size=5)
        assert r_noisy["contrast"].mean() > r_uniform["contrast"].mean()
