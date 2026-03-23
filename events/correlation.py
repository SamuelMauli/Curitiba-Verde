# events/correlation.py
"""Correlate historical events with NDVI changes."""
import numpy as np
from collections import defaultdict


def compute_event_ndvi_impact(
    ndvi_before: float,
    ndvi_after: float,
    threshold: float = 0.05,
) -> dict:
    """Compute NDVI impact of a single event.

    Compares mean NDVI of affected area 1 year before vs 1 year after.

    Args:
        ndvi_before: Mean NDVI of area 1 year before event.
        ndvi_after: Mean NDVI of area 1 year after event.
        threshold: Minimum delta to count as impact.

    Returns:
        Dict with delta, direction, significance.
    """
    delta = ndvi_after - ndvi_before
    if delta < -threshold:
        direction = "negativo"
    elif delta > threshold:
        direction = "positivo"
    else:
        direction = "neutro"

    return {
        "delta": float(delta),
        "direction": direction,
        "ndvi_before": float(ndvi_before),
        "ndvi_after": float(ndvi_after),
        "significant": abs(delta) > threshold,
    }


def compute_category_correlation(
    events_with_delta: list[dict],
) -> dict:
    """Compute mean NDVI impact per event category.

    Args:
        events_with_delta: List of dicts with 'categoria' and 'delta_ndvi' keys.

    Returns:
        Dict keyed by category with mean_delta, count, std_delta.
    """
    by_category = defaultdict(list)
    for e in events_with_delta:
        by_category[e["categoria"]].append(e["delta_ndvi"])

    result = {}
    for cat, deltas in by_category.items():
        arr = np.array(deltas)
        result[cat] = {
            "mean_delta": float(arr.mean()),
            "std_delta": float(arr.std()) if len(arr) > 1 else 0.0,
            "count": len(arr),
            "negative_count": int((arr < -0.05).sum()),
            "positive_count": int((arr > 0.05).sum()),
        }
    return result
