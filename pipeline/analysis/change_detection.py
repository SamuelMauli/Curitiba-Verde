"""Change detection — NDVI differences, class transitions, area quantification."""
import numpy as np
from pipeline.config import PIXEL_AREA_HA, CLASS_NAMES


def compute_ndvi_change(
    ndvi_before: np.ndarray,
    ndvi_after: np.ndarray,
    threshold: float = 0.15,
) -> np.ndarray:
    """Compute NDVI change map between two dates.

    Args:
        ndvi_before: NDVI array for earlier date.
        ndvi_after: NDVI array for later date.
        threshold: Minimum NDVI difference to count as change.

    Returns:
        Int8 array: -1 = loss, 0 = stable, 1 = gain.
    """
    diff = ndvi_after - ndvi_before
    change = np.zeros_like(diff, dtype=np.int8)
    change[diff < -threshold] = -1  # loss
    change[diff > threshold] = 1    # gain
    return change


def compute_class_transitions(
    before: np.ndarray,
    after: np.ndarray,
    n_classes: int = 5,
) -> np.ndarray:
    """Compute transition matrix: how many pixels changed from class A to B.

    Args:
        before: Classification map (earlier year).
        after: Classification map (later year).
        n_classes: Number of classes.

    Returns:
        (n_classes, n_classes) transition matrix.
        Row i, col j = pixels that went from class i+1 to class j+1.
    """
    matrix = np.zeros((n_classes, n_classes), dtype=np.int64)
    for i in range(n_classes):
        for j in range(n_classes):
            matrix[i, j] = ((before == (i + 1)) & (after == (j + 1))).sum()
    return matrix


def quantify_area_change(change_map: np.ndarray) -> dict:
    """Quantify area of loss, gain, and stable pixels.

    Args:
        change_map: Int8 array from compute_ndvi_change (-1, 0, 1).

    Returns:
        Dict with loss_ha, gain_ha, stable_ha, loss_pixels, gain_pixels.
    """
    loss_px = int((change_map == -1).sum())
    gain_px = int((change_map == 1).sum())
    stable_px = int((change_map == 0).sum())
    return {
        "loss_pixels": loss_px,
        "gain_pixels": gain_px,
        "stable_pixels": stable_px,
        "loss_ha": loss_px * PIXEL_AREA_HA,
        "gain_ha": gain_px * PIXEL_AREA_HA,
        "stable_ha": stable_px * PIXEL_AREA_HA,
        "net_change_ha": (gain_px - loss_px) * PIXEL_AREA_HA,
    }


def format_transition_matrix(matrix: np.ndarray) -> str:
    """Pretty-print the transition matrix with class names."""
    header = "De \\ Para  | " + " | ".join(
        f"{CLASS_NAMES.get(j+1, '?'):>12}" for j in range(matrix.shape[1])
    )
    lines = [header, "-" * len(header)]
    for i in range(matrix.shape[0]):
        row = f"{CLASS_NAMES.get(i+1, '?'):>10} | " + " | ".join(
            f"{matrix[i, j]:>12d}" for j in range(matrix.shape[1])
        )
        lines.append(row)
    return "\n".join(lines)
