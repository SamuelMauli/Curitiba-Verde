# pipeline/classification/validation.py
"""Validation metrics and consistency checks."""
import numpy as np
from sklearn.metrics import (
    accuracy_score, f1_score, confusion_matrix, cohen_kappa_score,
)
from sklearn.model_selection import KFold


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute classification metrics.

    Returns dict with accuracy, f1_macro, f1_per_class, kappa, confusion_matrix.
    """
    classes = np.unique(np.concatenate([y_true, y_pred]))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_per_class": {
            int(c): float(f)
            for c, f in zip(
                classes,
                f1_score(y_true, y_pred, average=None, labels=classes, zero_division=0),
            )
        },
        "kappa": float(cohen_kappa_score(y_true, y_pred)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=classes).tolist(),
    }


def cross_validate_spatial(
    classifier,
    X: np.ndarray,
    y: np.ndarray,
    coords: np.ndarray,
    n_folds: int = 5,
    block_size: float = 1000.0,
) -> list[dict]:
    """Spatial cross-validation using geographic blocks.

    Groups samples into spatial blocks to avoid autocorrelation leakage.

    Args:
        classifier: Instance with train/evaluate methods.
        X: Feature matrix.
        y: Labels.
        coords: (n_samples, 2) array of [x, y] coordinates.
        n_folds: Number of CV folds.
        block_size: Block size in CRS units (meters).

    Returns:
        List of metric dicts per fold.
    """
    # Assign each sample to a spatial block
    block_x = (coords[:, 0] / block_size).astype(int)
    block_y = (coords[:, 1] / block_size).astype(int)
    block_ids = block_x * 10000 + block_y  # unique block ID

    unique_blocks = np.unique(block_ids)
    kf = KFold(n_splits=min(n_folds, len(unique_blocks)), shuffle=True, random_state=42)

    results = []
    for train_blocks, test_blocks in kf.split(unique_blocks):
        train_block_set = set(unique_blocks[train_blocks])
        test_block_set = set(unique_blocks[test_blocks])

        train_mask = np.isin(block_ids, list(train_block_set))
        test_mask = np.isin(block_ids, list(test_block_set))

        from pipeline.classification.ensemble import EnsembleClassifier
        fold_clf = EnsembleClassifier()
        fold_clf.train(X[train_mask], y[train_mask])
        metrics = fold_clf.evaluate(X[test_mask], y[test_mask])
        results.append(metrics)

    return results


def compare_with_mapbiomas(
    our_classification: np.ndarray,
    mapbiomas_classification: np.ndarray,
) -> dict:
    """Compare our classification against MapBiomas pixel-by-pixel.

    Args:
        our_classification: 2D array from our ensemble.
        mapbiomas_classification: 2D array from MapBiomas (reclassified to 5 classes).

    Returns:
        Dict with agreement percentage and per-class agreement.
    """
    valid = (our_classification > 0) & (mapbiomas_classification > 0)
    ours = our_classification[valid]
    mb = mapbiomas_classification[valid]

    agreement = (ours == mb).sum() / len(ours) * 100
    per_class = {}
    for cls in np.unique(mb):
        cls_mask = mb == cls
        if cls_mask.sum() > 0:
            per_class[int(cls)] = float(
                (ours[cls_mask] == cls).sum() / cls_mask.sum() * 100
            )

    return {
        "overall_agreement_pct": float(agreement),
        "per_class_agreement_pct": per_class,
        "total_pixels_compared": int(valid.sum()),
    }


def check_temporal_consistency(
    classification_maps: list[np.ndarray],
) -> list[np.ndarray]:
    """Remove impossible class transitions (flip-flops).

    Rule: if a pixel goes A→B→A across 3 consecutive years,
    the third year is corrected to B (no reversion).

    This prevents noise from creating artificial forest regrowth
    in 1-year windows.

    Args:
        classification_maps: List of 2D arrays ordered by year.

    Returns:
        Corrected list of classification maps.
    """
    if len(classification_maps) < 3:
        return classification_maps

    corrected = [m.copy() for m in classification_maps]

    for i in range(2, len(corrected)):
        prev2 = corrected[i - 2]
        prev1 = corrected[i - 1]
        curr = corrected[i]

        # Detect flip-flops: prev2 == curr AND prev2 != prev1
        flip_flop = (prev2 == curr) & (prev2 != prev1)
        # Correct: keep the intermediate value (prev1)
        corrected[i] = np.where(flip_flop, prev1, curr)

    return corrected
