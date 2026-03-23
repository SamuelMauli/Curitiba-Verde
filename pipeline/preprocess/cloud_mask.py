"""Cloud masking for Landsat QA_PIXEL band."""
import numpy as np


# Landsat Collection 2 QA_PIXEL bit positions
_CLOUD_BIT = 3       # Cloud
_CLOUD_SHADOW_BIT = 4  # Cloud shadow
_CIRRUS_BIT = 2      # Cirrus (high confidence)


def create_cloud_mask(
    qa_band: np.ndarray,
    mask_cloud: bool = True,
    mask_shadow: bool = True,
    mask_cirrus: bool = True,
) -> np.ndarray:
    """Create boolean mask from Landsat QA_PIXEL band.

    Args:
        qa_band: 2D uint16 array from QA_PIXEL band.
        mask_cloud: Mask cloud pixels (bit 3).
        mask_shadow: Mask cloud shadow pixels (bit 4).
        mask_cirrus: Mask cirrus pixels (bit 2).

    Returns:
        Boolean array — True where pixel should be masked (cloudy).
    """
    mask = np.zeros(qa_band.shape, dtype=bool)
    if mask_cloud:
        mask |= (qa_band & (1 << _CLOUD_BIT)) != 0
    if mask_shadow:
        mask |= (qa_band & (1 << _CLOUD_SHADOW_BIT)) != 0
    if mask_cirrus:
        mask |= (qa_band & (1 << _CIRRUS_BIT)) != 0
    return mask


def apply_cloud_mask(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Apply cloud mask to data array — set masked pixels to NaN.

    Args:
        data: 2D float array.
        mask: Boolean array — True = cloudy.

    Returns:
        Copy of data with masked pixels set to NaN.
    """
    result = data.copy().astype(np.float32)
    result[mask] = np.nan
    return result
