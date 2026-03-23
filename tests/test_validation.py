# tests/test_validation.py
import numpy as np
import pytest
from pipeline.classification.validation import (
    compute_metrics, cross_validate_spatial,
    compare_with_mapbiomas, check_temporal_consistency,
)


class TestComputeMetrics:
    def test_perfect_predictions(self):
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1, 2, 3, 4, 5])
        metrics = compute_metrics(y_true, y_pred)
        assert metrics["accuracy"] == 1.0
        assert metrics["kappa"] == 1.0

    def test_random_predictions_low_accuracy(self):
        rng = np.random.RandomState(42)
        y_true = rng.randint(1, 6, 1000)
        y_pred = rng.randint(1, 6, 1000)
        metrics = compute_metrics(y_true, y_pred)
        assert metrics["accuracy"] < 0.5

    def test_returns_all_keys(self):
        y_true = np.array([1, 2, 3])
        y_pred = np.array([1, 2, 2])
        metrics = compute_metrics(y_true, y_pred)
        assert "accuracy" in metrics
        assert "f1_macro" in metrics
        assert "f1_per_class" in metrics
        assert "kappa" in metrics
        assert "confusion_matrix" in metrics


class TestTemporalConsistency:
    def test_flip_flop_detected(self):
        """Forest→Urban→Forest should be flagged."""
        maps = [
            np.array([[1]]),  # year 1: forest
            np.array([[3]]),  # year 2: urban
            np.array([[1]]),  # year 3: forest (flip-flop!)
        ]
        corrected = check_temporal_consistency(maps)
        # Year 3 should stay urban (no flip back)
        assert corrected[2][0, 0] == 3

    def test_valid_transition_preserved(self):
        """Forest→Urban→Urban is a valid transition."""
        maps = [
            np.array([[1]]),  # forest
            np.array([[3]]),  # urban
            np.array([[3]]),  # urban (consistent)
        ]
        corrected = check_temporal_consistency(maps)
        assert corrected[0][0, 0] == 1
        assert corrected[1][0, 0] == 3
        assert corrected[2][0, 0] == 3
