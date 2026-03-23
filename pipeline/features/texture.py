# pipeline/features/texture.py
"""GLCM texture features — contrast and homogeneity."""
import numpy as np
from skimage.feature import graycomatrix, graycoprops


def compute_glcm_features(
    band: np.ndarray,
    window_size: int = 5,
    levels: int = 64,
    distances: list[int] | None = None,
    angles: list[float] | None = None,
) -> dict[str, np.ndarray]:
    """Compute GLCM contrast and homogeneity over sliding windows.

    Args:
        band: 2D array, uint8 (0-255). If float, will be quantized.
        window_size: Size of the sliding window (must be odd).
        levels: Number of gray levels for GLCM (default 64 for speed).
        distances: GLCM distances (default [1]).
        angles: GLCM angles in radians (default [0]).

    Returns:
        Dict with "contrast" and "homogeneity" arrays, same shape as input.
    """
    if distances is None:
        distances = [1]
    if angles is None:
        angles = [0]

    # Quantize to fewer levels for speed
    if band.dtype != np.uint8:
        band = np.clip(band, 0, 255).astype(np.uint8)
    band_quantized = (band / 256 * levels).astype(np.uint8)

    h, w = band.shape
    pad = window_size // 2
    contrast = np.zeros((h, w), dtype=np.float32)
    homogeneity = np.zeros((h, w), dtype=np.float32)

    # Pad the image
    padded = np.pad(band_quantized, pad, mode="reflect")

    for i in range(h):
        for j in range(w):
            window = padded[i:i + window_size, j:j + window_size]
            glcm = graycomatrix(
                window, distances=distances, angles=angles,
                levels=levels, symmetric=True, normed=True,
            )
            contrast[i, j] = graycoprops(glcm, "contrast")[0, 0]
            homogeneity[i, j] = graycoprops(glcm, "homogeneity")[0, 0]

    return {"contrast": contrast, "homogeneity": homogeneity}
