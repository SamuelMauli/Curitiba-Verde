# pipeline/classification/postprocess.py
"""Post-processing for classification maps — spatial filters and consistency."""
import numpy as np
from scipy.ndimage import generic_filter, label, binary_dilation


def _mode_func(values):
    """Return the most common value in a window."""
    vals, counts = np.unique(values[values > 0], return_counts=True)
    if len(vals) == 0:
        return 0
    return vals[np.argmax(counts)]


def apply_mode_filter(
    classification: np.ndarray, window_size: int = 3
) -> np.ndarray:
    """Apply mode filter to remove isolated misclassified pixels.

    Each pixel adopts the most frequent class in its neighborhood.

    Args:
        classification: 2D uint8 array with class labels (1-5).
        window_size: Filter window size (must be odd).

    Returns:
        Filtered classification array.
    """
    return generic_filter(
        classification.astype(np.float64),
        _mode_func,
        size=window_size,
        mode="nearest",
    ).astype(np.uint8)


def apply_mmu(
    classification: np.ndarray, min_pixels: int = 6
) -> np.ndarray:
    """Apply Minimum Mapping Unit — absorb small patches.

    Connected components smaller than min_pixels are replaced
    by the most common neighboring class.

    Args:
        classification: 2D uint8 array.
        min_pixels: Minimum patch size in pixels (default 6 ≈ 0.5ha at 30m).

    Returns:
        Filtered classification.
    """
    result = classification.copy()
    for cls in np.unique(classification):
        if cls == 0:
            continue
        mask = classification == cls
        labeled, n_features = label(mask)
        for i in range(1, n_features + 1):
            component = labeled == i
            if component.sum() < min_pixels:
                # Find dominant neighbor class
                dilated = binary_dilation(component, iterations=1)
                border = dilated & ~component
                border_vals = classification[border]
                border_vals = border_vals[border_vals != cls]
                if len(border_vals) > 0:
                    vals, counts = np.unique(border_vals, return_counts=True)
                    dominant = vals[np.argmax(counts)]
                    result[component] = dominant
    return result


def apply_water_consistency(
    classification: np.ndarray,
    water_mask: np.ndarray,
    buffer_pixels: int = 3,
    water_class: int = 5,
) -> np.ndarray:
    """Remove water pixels that are far from known water bodies.

    Args:
        classification: 2D uint8 array.
        water_mask: Boolean mask of known water bodies (from shapefile).
        buffer_pixels: Maximum distance from known water.
        water_class: Class ID for water (default 5).

    Returns:
        Corrected classification.
    """
    result = classification.copy()
    # Dilate known water mask to create buffer zone
    buffered = binary_dilation(water_mask, iterations=buffer_pixels)
    # Pixels classified as water but outside buffer → reclassify
    isolated_water = (classification == water_class) & ~buffered
    if isolated_water.any():
        # Replace with mode of non-water neighbors
        result[isolated_water] = 0  # temporarily mark
        result = apply_mode_filter(result, window_size=3)
    return result


def postprocess_classification(
    classification: np.ndarray,
    water_mask: np.ndarray | None = None,
    mode_window: int = 3,
    min_pixels: int = 6,
) -> np.ndarray:
    """Apply full post-processing pipeline.

    Order: mode filter → MMU → water consistency.
    """
    result = apply_mode_filter(classification, window_size=mode_window)
    result = apply_mmu(result, min_pixels=min_pixels)
    if water_mask is not None:
        result = apply_water_consistency(result, water_mask)
    return result
