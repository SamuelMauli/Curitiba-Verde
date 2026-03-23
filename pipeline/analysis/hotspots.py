"""Detect deforestation hotspots — areas with highest cumulative loss."""
import numpy as np
from pipeline.config import PIXEL_AREA_HA


def compute_cumulative_loss(
    change_maps: list[np.ndarray],
) -> np.ndarray:
    """Compute cumulative vegetation loss across all years.

    Args:
        change_maps: List of change maps (-1/0/1) ordered by year pair.

    Returns:
        2D array: count of years with loss per pixel (0 to N).
    """
    cumulative = np.zeros_like(change_maps[0], dtype=np.int16)
    for cm in change_maps:
        cumulative += (cm == -1).astype(np.int16)
    return cumulative


def identify_hotspots(
    cumulative_loss: np.ndarray,
    min_loss_years: int = 3,
) -> dict:
    """Identify hotspot regions where loss occurred repeatedly.

    Args:
        cumulative_loss: Array from compute_cumulative_loss.
        min_loss_years: Minimum years of loss to be a hotspot.

    Returns:
        Dict with hotspot mask, total area, statistics.
    """
    hotspot_mask = cumulative_loss >= min_loss_years
    hotspot_pixels = int(hotspot_mask.sum())
    return {
        "hotspot_mask": hotspot_mask,
        "hotspot_pixels": hotspot_pixels,
        "hotspot_area_ha": float(hotspot_pixels * PIXEL_AREA_HA),
        "max_loss_years": int(cumulative_loss.max()),
        "mean_loss_years": float(cumulative_loss[cumulative_loss > 0].mean())
        if (cumulative_loss > 0).any() else 0.0,
    }
