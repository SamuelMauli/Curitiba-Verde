# pipeline/features/indices.py
"""Spectral index computation — NDVI, NDWI, NDBI, SAVI, EVI."""
import numpy as np


def _safe_normalized_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute (a - b) / (a + b), handling division by zero."""
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            (a + b) == 0,
            0.0,
            (a - b) / (a + b),
        )
    return np.clip(result.astype(np.float32), -1.0, 1.0)


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalized Difference Vegetation Index.

    NDVI = (NIR - RED) / (NIR + RED)
    High values (>0.4) indicate vegetation.
    """
    return _safe_normalized_diff(nir, red)


def compute_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalized Difference Water Index (McFeeters).

    NDWI = (GREEN - NIR) / (GREEN + NIR)
    Positive values indicate water bodies.
    """
    return _safe_normalized_diff(green, nir)


def compute_ndbi(swir: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalized Difference Built-up Index.

    NDBI = (SWIR - NIR) / (SWIR + NIR)
    Positive values indicate built-up/urban areas.
    """
    return _safe_normalized_diff(swir, nir)


def compute_savi(nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray:
    """Soil-Adjusted Vegetation Index.

    SAVI = ((NIR - RED) / (NIR + RED + L)) * (1 + L)
    Better than NDVI for areas with exposed soil.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            (nir + red + L) == 0,
            0.0,
            ((nir - red) / (nir + red + L)) * (1 + L),
        )
    return np.clip(result.astype(np.float32), -1.0, 1.0)


def compute_evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray,
                G: float = 2.5, C1: float = 6.0, C2: float = 7.5,
                L_evi: float = 1.0) -> np.ndarray:
    """Enhanced Vegetation Index.

    EVI = G * (NIR - RED) / (NIR + C1*RED - C2*BLUE + L)
    Better for dense vegetation (corrects atmospheric influence).
    """
    denominator = nir + C1 * red - C2 * blue + L_evi
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            denominator == 0,
            0.0,
            G * (nir - red) / denominator,
        )
    return np.clip(result.astype(np.float32), -1.0, 1.0)


def compute_all_indices(bands: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Compute all spectral indices from a dict of named bands.

    Args:
        bands: Dict with keys "blue", "green", "red", "nir", "swir1", "swir2".
               Each value is a 2D numpy array (H, W).

    Returns:
        Dict with keys "ndvi", "ndwi", "ndbi", "savi", "evi".
    """
    return {
        "ndvi": compute_ndvi(bands["nir"], bands["red"]),
        "ndwi": compute_ndwi(bands["green"], bands["nir"]),
        "ndbi": compute_ndbi(bands["swir1"], bands["nir"]),
        "savi": compute_savi(bands["nir"], bands["red"]),
        "evi": compute_evi(bands["nir"], bands["red"], bands["blue"]),
    }
