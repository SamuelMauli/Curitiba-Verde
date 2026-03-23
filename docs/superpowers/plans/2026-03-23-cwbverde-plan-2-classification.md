# CwbVerde Plan 2: ML Classification — Ensemble, Validation, Change Detection

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ensemble classifier (Random Forest + XGBoost + SVM), post-processing spatial filters, multi-level validation framework, and change detection module that produces classified land cover maps and deforestation analysis for all 25 years.

**Architecture:** Abstract `BaseClassifier` interface with `EnsembleClassifier` implementation combining 3 models via soft voting. Post-processing cleans spatial noise. Validation cross-checks against MapBiomas. Change detection compares NDVI/classes across years.

**Tech Stack:** scikit-learn, xgboost, numpy, rasterio, geopandas, pandas, pytest

**Spec Reference:** `docs/superpowers/specs/2026-03-23-cwbverde-design.md` — Sections 3 (Modules 4-5), 11

**Depends on:** Plan 1 (Pipeline Core) — needs feature stacks and NDVI rasters

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `pipeline/classification/__init__.py` | Package init |
| Create | `pipeline/classification/base.py` | BaseClassifier ABC |
| Create | `pipeline/classification/ensemble.py` | RF + XGBoost + SVM ensemble |
| Create | `pipeline/classification/postprocess.py` | Mode filter, MMU, water consistency |
| Create | `pipeline/classification/validation.py` | Metrics, confusion matrix, cross-val |
| Create | `pipeline/analysis/__init__.py` | Package init |
| Create | `pipeline/analysis/change_detection.py` | NDVI diff, class transitions |
| Create | `pipeline/analysis/statistics.py` | Stats per bairro/year |
| Create | `pipeline/analysis/hotspots.py` | Cumulative loss hotspots |
| Create | `tests/test_classification.py` | Test ensemble classifier |
| Create | `tests/test_postprocess.py` | Test spatial filters |
| Create | `tests/test_validation.py` | Test metrics computation |
| Create | `tests/test_change_detection.py` | Test change detection |
| Create | `tests/test_statistics.py` | Test stats aggregation |

---

## Task 1: BaseClassifier ABC

**Files:**
- Create: `pipeline/classification/base.py`

- [ ] **Step 1: Write the abstract base class**

```python
# pipeline/classification/base.py
"""Abstract base classifier interface."""
from abc import ABC, abstractmethod
import numpy as np


class BaseClassifier(ABC):
    """Interface for all land cover classifiers.

    All classifiers (Ensemble, U-Net, Hybrid) implement this interface
    to ensure consistent API across the pipeline.
    """

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the classifier.

        Args:
            X: Feature matrix (n_samples, n_features).
            y: Labels (n_samples,) with values 1-5.
        """
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels.

        Args:
            X: Feature matrix (n_samples, n_features).

        Returns:
            Predicted labels (n_samples,).
        """
        ...

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities.

        Args:
            X: Feature matrix (n_samples, n_features).

        Returns:
            Probability matrix (n_samples, n_classes).
        """
        ...

    @abstractmethod
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        """Evaluate on test set.

        Args:
            X_test: Test features.
            y_test: True labels.

        Returns:
            Dict with metrics (f1, kappa, confusion_matrix, etc.)
        """
        ...

    @abstractmethod
    def save(self, path: str) -> None:
        """Save model to disk."""
        ...

    @abstractmethod
    def load(self, path: str) -> None:
        """Load model from disk."""
        ...
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/classification/__init__.py pipeline/classification/base.py
git commit -m "feat: add BaseClassifier abstract interface"
```

---

## Task 2: Ensemble Classifier (RF + XGBoost + SVM)

**Files:**
- Create: `pipeline/classification/ensemble.py`
- Create: `tests/test_classification.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_classification.py
import numpy as np
import pytest
from pipeline.classification.ensemble import EnsembleClassifier


@pytest.fixture
def sample_data():
    """Create synthetic training data for 5 classes."""
    rng = np.random.RandomState(42)
    n_per_class = 100
    n_features = 11  # 6 bands + 5 indices

    X_list, y_list = [], []
    for cls in range(1, 6):
        # Each class has a distinct centroid
        centroid = rng.uniform(0, 1, n_features) * cls
        X_cls = centroid + rng.normal(0, 0.2, (n_per_class, n_features))
        y_cls = np.full(n_per_class, cls)
        X_list.append(X_cls)
        y_list.append(y_cls)

    X = np.vstack(X_list).astype(np.float32)
    y = np.concatenate(y_list).astype(np.int32)
    return X, y


class TestEnsembleClassifier:
    def test_train_runs(self, sample_data):
        X, y = sample_data
        clf = EnsembleClassifier()
        clf.train(X, y)
        assert clf._is_trained

    def test_predict_shape(self, sample_data):
        X, y = sample_data
        clf = EnsembleClassifier()
        clf.train(X, y)
        preds = clf.predict(X[:10])
        assert preds.shape == (10,)

    def test_predict_valid_classes(self, sample_data):
        X, y = sample_data
        clf = EnsembleClassifier()
        clf.train(X, y)
        preds = clf.predict(X)
        assert set(np.unique(preds)).issubset({1, 2, 3, 4, 5})

    def test_predict_proba_shape(self, sample_data):
        X, y = sample_data
        clf = EnsembleClassifier()
        clf.train(X, y)
        proba = clf.predict_proba(X[:10])
        assert proba.shape == (10, 5)
        # Probabilities sum to 1
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=0.01)

    def test_accuracy_above_threshold(self, sample_data):
        """Ensemble should achieve reasonable accuracy on well-separated data."""
        X, y = sample_data
        clf = EnsembleClassifier()
        clf.train(X[:400], y[:400])
        metrics = clf.evaluate(X[400:], y[400:])
        assert metrics["accuracy"] > 0.7

    def test_evaluate_returns_metrics(self, sample_data):
        X, y = sample_data
        clf = EnsembleClassifier()
        clf.train(X[:400], y[:400])
        metrics = clf.evaluate(X[400:], y[400:])
        assert "accuracy" in metrics
        assert "f1_per_class" in metrics
        assert "kappa" in metrics
        assert "confusion_matrix" in metrics

    def test_save_and_load(self, sample_data, tmp_path):
        X, y = sample_data
        clf = EnsembleClassifier()
        clf.train(X, y)
        preds_before = clf.predict(X[:10])

        model_path = str(tmp_path / "model.joblib")
        clf.save(model_path)

        clf2 = EnsembleClassifier()
        clf2.load(model_path)
        preds_after = clf2.predict(X[:10])

        np.testing.assert_array_equal(preds_before, preds_after)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_classification.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/classification/ensemble.py
"""Ensemble classifier — Random Forest + XGBoost + SVM with soft voting."""
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, f1_score, confusion_matrix, cohen_kappa_score,
)
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from pipeline.classification.base import BaseClassifier


class EnsembleClassifier(BaseClassifier):
    """Soft-voting ensemble of RF + XGBoost + SVM.

    Each model predicts class probabilities, which are averaged
    (weighted by per-model F1 score) to produce the final prediction.
    """

    def __init__(
        self,
        rf_n_estimators: int = 500,
        rf_max_depth: int = 20,
        xgb_n_estimators: int = 300,
        xgb_max_depth: int = 10,
        svm_C: float = 10.0,
        svm_gamma: str = "scale",
    ):
        self._rf = RandomForestClassifier(
            n_estimators=rf_n_estimators,
            max_depth=rf_max_depth,
            random_state=42,
            n_jobs=-1,
        )
        self._xgb = XGBClassifier(
            n_estimators=xgb_n_estimators,
            max_depth=xgb_max_depth,
            random_state=42,
            n_jobs=-1,
            use_label_encoder=False,
            eval_metric="mlogloss",
        )
        self._svm = SVC(
            C=svm_C,
            gamma=svm_gamma,
            kernel="rbf",
            probability=True,
            random_state=42,
        )
        self._scaler = StandardScaler()
        self._weights = np.array([1.0, 1.0, 1.0])  # calibrated after training
        self._classes = None
        self._is_trained = False

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train all 3 models and calibrate ensemble weights."""
        self._classes = np.unique(y)

        # Scale features (important for SVM)
        X_scaled = self._scaler.fit_transform(X)

        # XGBoost needs 0-indexed labels
        y_xgb = y - y.min()

        # Train models
        self._rf.fit(X_scaled, y)
        self._xgb.fit(X_scaled, y_xgb)
        self._svm.fit(X_scaled, y)

        # Calibrate weights using training F1 (macro)
        rf_f1 = f1_score(y, self._rf.predict(X_scaled), average="macro")
        xgb_preds = self._xgb.predict(X_scaled) + y.min()
        xgb_f1 = f1_score(y, xgb_preds, average="macro")
        svm_f1 = f1_score(y, self._svm.predict(X_scaled), average="macro")

        total = rf_f1 + xgb_f1 + svm_f1
        self._weights = np.array([rf_f1, xgb_f1, svm_f1]) / total
        self._is_trained = True

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Weighted average of probability predictions."""
        X_scaled = self._scaler.transform(X)

        rf_proba = self._rf.predict_proba(X_scaled)
        xgb_proba = self._xgb.predict_proba(X_scaled)
        svm_proba = self._svm.predict_proba(X_scaled)

        # Weighted average
        avg_proba = (
            self._weights[0] * rf_proba
            + self._weights[1] * xgb_proba
            + self._weights[2] * svm_proba
        )
        return avg_proba

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict classes from ensemble probabilities."""
        proba = self.predict_proba(X)
        indices = np.argmax(proba, axis=1)
        return self._classes[indices]

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        """Compute accuracy, F1, kappa, confusion matrix."""
        preds = self.predict(X_test)
        return {
            "accuracy": accuracy_score(y_test, preds),
            "f1_macro": f1_score(y_test, preds, average="macro"),
            "f1_per_class": {
                int(c): float(f)
                for c, f in zip(
                    self._classes,
                    f1_score(y_test, preds, average=None),
                )
            },
            "kappa": cohen_kappa_score(y_test, preds),
            "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
        }

    def save(self, path: str) -> None:
        """Save entire ensemble to disk."""
        joblib.dump({
            "rf": self._rf,
            "xgb": self._xgb,
            "svm": self._svm,
            "scaler": self._scaler,
            "weights": self._weights,
            "classes": self._classes,
        }, path)

    def load(self, path: str) -> None:
        """Load ensemble from disk."""
        data = joblib.load(path)
        self._rf = data["rf"]
        self._xgb = data["xgb"]
        self._svm = data["svm"]
        self._scaler = data["scaler"]
        self._weights = data["weights"]
        self._classes = data["classes"]
        self._is_trained = True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_classification.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/classification/ensemble.py tests/test_classification.py
git commit -m "feat: add ensemble classifier (RF + XGBoost + SVM)"
```

---

## Task 3: Post-Processing (Mode Filter, MMU, Water Consistency)

**Files:**
- Create: `pipeline/classification/postprocess.py`
- Create: `tests/test_postprocess.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_postprocess.py
import numpy as np
import pytest
from pipeline.classification.postprocess import (
    apply_mode_filter, apply_mmu, apply_water_consistency,
    postprocess_classification,
)


class TestModeFilter:
    def test_isolated_pixel_corrected(self):
        """A single pixel surrounded by class 1 should become class 1."""
        data = np.ones((5, 5), dtype=np.uint8)
        data[2, 2] = 3  # isolated pixel
        result = apply_mode_filter(data, window_size=3)
        assert result[2, 2] == 1

    def test_large_region_preserved(self):
        """A large block of class 2 should remain class 2."""
        data = np.ones((10, 10), dtype=np.uint8)
        data[3:7, 3:7] = 2  # 4x4 block
        result = apply_mode_filter(data, window_size=3)
        assert result[5, 5] == 2

    def test_output_shape(self):
        data = np.random.randint(1, 6, (50, 50), dtype=np.uint8)
        result = apply_mode_filter(data, window_size=3)
        assert result.shape == (50, 50)


class TestMMU:
    def test_small_patch_absorbed(self):
        """A 2-pixel patch (< MMU) gets absorbed by surrounding class."""
        data = np.ones((10, 10), dtype=np.uint8)
        data[4, 4] = 3
        data[4, 5] = 3  # 2-pixel patch
        result = apply_mmu(data, min_pixels=5)
        assert result[4, 4] == 1
        assert result[4, 5] == 1

    def test_large_patch_preserved(self):
        """A 25-pixel patch (>= MMU) stays unchanged."""
        data = np.ones((20, 20), dtype=np.uint8)
        data[5:10, 5:10] = 2  # 25-pixel patch
        result = apply_mmu(data, min_pixels=5)
        assert result[7, 7] == 2


class TestWaterConsistency:
    def test_isolated_water_removed(self):
        """Water pixel far from known water body → reclassified."""
        classification = np.ones((20, 20), dtype=np.uint8)  # all forest
        classification[10, 10] = 5  # isolated water pixel
        water_mask = np.zeros((20, 20), dtype=bool)  # no known water nearby
        result = apply_water_consistency(classification, water_mask, buffer_pixels=3)
        assert result[10, 10] != 5

    def test_water_near_known_body_preserved(self):
        """Water pixel near known water body → stays water."""
        classification = np.ones((20, 20), dtype=np.uint8)
        classification[10, 10] = 5
        water_mask = np.zeros((20, 20), dtype=bool)
        water_mask[10, 11] = True  # known water adjacent
        result = apply_water_consistency(classification, water_mask, buffer_pixels=3)
        assert result[10, 10] == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_postprocess.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_postprocess.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/classification/postprocess.py tests/test_postprocess.py
git commit -m "feat: add post-processing (mode filter, MMU, water consistency)"
```

---

## Task 4: Validation Framework

**Files:**
- Create: `pipeline/classification/validation.py`
- Create: `tests/test_validation.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_validation.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_validation.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/classification/validation.py tests/test_validation.py
git commit -m "feat: add validation framework (metrics, spatial CV, temporal consistency)"
```

---

## Task 5: Change Detection

**Files:**
- Create: `pipeline/analysis/change_detection.py`
- Create: `tests/test_change_detection.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_change_detection.py
import numpy as np
import pytest
from pipeline.analysis.change_detection import (
    compute_ndvi_change, compute_class_transitions,
    quantify_area_change,
)
from pipeline.config import PIXEL_AREA_HA


class TestNDVIChange:
    def test_loss_detected(self):
        """NDVI decrease → negative change."""
        ndvi_before = np.array([[0.8, 0.7], [0.6, 0.5]])
        ndvi_after = np.array([[0.3, 0.7], [0.6, 0.1]])
        change = compute_ndvi_change(ndvi_before, ndvi_after, threshold=0.15)
        assert change[0, 0] == -1  # loss
        assert change[1, 1] == -1  # loss
        assert change[0, 1] == 0   # no change

    def test_gain_detected(self):
        ndvi_before = np.array([[0.2]])
        ndvi_after = np.array([[0.6]])
        change = compute_ndvi_change(ndvi_before, ndvi_after, threshold=0.15)
        assert change[0, 0] == 1  # gain

    def test_below_threshold_is_stable(self):
        ndvi_before = np.array([[0.5]])
        ndvi_after = np.array([[0.45]])
        change = compute_ndvi_change(ndvi_before, ndvi_after, threshold=0.15)
        assert change[0, 0] == 0  # stable


class TestClassTransitions:
    def test_forest_to_urban(self):
        before = np.array([[1, 1], [1, 1]], dtype=np.uint8)
        after = np.array([[3, 1], [1, 3]], dtype=np.uint8)
        matrix = compute_class_transitions(before, after, n_classes=5)
        assert matrix[0, 2] == 2  # class 1 → class 3: 2 pixels

    def test_no_change(self):
        data = np.ones((5, 5), dtype=np.uint8)
        matrix = compute_class_transitions(data, data, n_classes=5)
        assert matrix[0, 0] == 25  # all stay class 1


class TestQuantifyArea:
    def test_area_calculation(self):
        change = np.zeros((100, 100), dtype=np.int8)
        change[:10, :] = -1  # 1000 pixels lost
        stats = quantify_area_change(change)
        expected_ha = 1000 * PIXEL_AREA_HA
        assert stats["loss_ha"] == pytest.approx(expected_ha, abs=0.1)

    def test_gain_area(self):
        change = np.zeros((50, 50), dtype=np.int8)
        change[:5, :5] = 1  # 25 pixels gained
        stats = quantify_area_change(change)
        expected_ha = 25 * PIXEL_AREA_HA
        assert stats["gain_ha"] == pytest.approx(expected_ha, abs=0.1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_change_detection.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/analysis/change_detection.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_change_detection.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/analysis/__init__.py pipeline/analysis/change_detection.py tests/test_change_detection.py
git commit -m "feat: add change detection (NDVI diff, transitions, area stats)"
```

---

## Task 6: Statistics Aggregation

**Files:**
- Create: `pipeline/analysis/statistics.py`
- Create: `tests/test_statistics.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_statistics.py
import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import box
from pipeline.analysis.statistics import (
    compute_zonal_stats, compute_yearly_summary,
)


@pytest.fixture
def mock_bairros():
    """Two bairros covering left and right halves."""
    return gpd.GeoDataFrame({
        "nome": ["Bairro A", "Bairro B"],
        "geometry": [
            box(-49.30, -25.50, -49.25, -25.40),  # left
            box(-49.25, -25.50, -49.20, -25.40),  # right
        ]
    }, crs="EPSG:4326")


class TestComputeZonalStats:
    def test_returns_per_bairro_stats(self, mock_bairros):
        ndvi = np.zeros((100, 100), dtype=np.float32)
        ndvi[:, :50] = 0.7   # left half: high NDVI
        ndvi[:, 50:] = 0.2   # right half: low NDVI
        from rasterio.transform import from_bounds
        transform = from_bounds(-49.30, -25.50, -49.20, -25.40, 100, 100)

        stats = compute_zonal_stats(ndvi, mock_bairros, transform, "EPSG:4326")
        assert len(stats) == 2
        assert stats[0]["nome"] == "Bairro A"
        assert stats[0]["ndvi_mean"] > 0.5
        assert stats[1]["ndvi_mean"] < 0.4


class TestYearlySummary:
    def test_summary_has_year_and_metrics(self):
        ndvi = np.random.uniform(0, 1, (50, 50)).astype(np.float32)
        classification = np.random.randint(1, 6, (50, 50)).astype(np.uint8)
        summary = compute_yearly_summary(ndvi, classification, year=2020)
        assert summary["year"] == 2020
        assert "ndvi_mean" in summary
        assert "green_area_ha" in summary
        assert "class_distribution" in summary
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_statistics.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# pipeline/analysis/statistics.py
"""Zonal statistics and yearly summaries."""
import numpy as np
import geopandas as gpd
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from pipeline.config import PIXEL_AREA_HA, CLASS_NAMES


def compute_zonal_stats(
    ndvi: np.ndarray,
    bairros: gpd.GeoDataFrame,
    transform: Affine,
    crs: str,
) -> list[dict]:
    """Compute NDVI statistics per bairro.

    Args:
        ndvi: 2D NDVI array.
        bairros: GeoDataFrame with bairro geometries and 'nome' column.
        transform: Rasterio transform of the NDVI raster.
        crs: CRS of the NDVI raster.

    Returns:
        List of dicts, one per bairro, with stats.
    """
    bairros_proj = bairros.to_crs(crs)
    results = []

    for _, row in bairros_proj.iterrows():
        mask = geometry_mask(
            [row.geometry],
            out_shape=ndvi.shape,
            transform=transform,
            invert=True,
        )
        pixels = ndvi[mask]
        valid = pixels[~np.isnan(pixels)]

        if len(valid) == 0:
            results.append({
                "nome": row.get("nome", "Unknown"),
                "ndvi_mean": 0.0,
                "ndvi_std": 0.0,
                "green_area_ha": 0.0,
                "total_pixels": 0,
            })
            continue

        green_pixels = (valid > 0.3).sum()
        results.append({
            "nome": row.get("nome", "Unknown"),
            "ndvi_mean": float(valid.mean()),
            "ndvi_std": float(valid.std()),
            "green_area_ha": float(green_pixels * PIXEL_AREA_HA),
            "total_pixels": int(len(valid)),
        })

    return results


def compute_yearly_summary(
    ndvi: np.ndarray,
    classification: np.ndarray,
    year: int,
) -> dict:
    """Compute summary statistics for a single year.

    Args:
        ndvi: 2D NDVI array.
        classification: 2D classification array (1-5).
        year: Year label.

    Returns:
        Dict with year, ndvi stats, green area, class distribution.
    """
    valid_ndvi = ndvi[~np.isnan(ndvi)]
    total_pixels = (classification > 0).sum()
    green_pixels = ((classification == 1) | (classification == 2)).sum()

    class_dist = {}
    for cls_id, cls_name in CLASS_NAMES.items():
        count = int((classification == cls_id).sum())
        class_dist[cls_name] = {
            "pixels": count,
            "hectares": float(count * PIXEL_AREA_HA),
            "percent": float(count / total_pixels * 100) if total_pixels > 0 else 0,
        }

    return {
        "year": year,
        "ndvi_mean": float(valid_ndvi.mean()) if len(valid_ndvi) > 0 else 0,
        "ndvi_std": float(valid_ndvi.std()) if len(valid_ndvi) > 0 else 0,
        "green_area_ha": float(green_pixels * PIXEL_AREA_HA),
        "total_area_ha": float(total_pixels * PIXEL_AREA_HA),
        "green_percent": float(green_pixels / total_pixels * 100) if total_pixels > 0 else 0,
        "class_distribution": class_dist,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_statistics.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/analysis/statistics.py tests/test_statistics.py
git commit -m "feat: add zonal statistics and yearly summary computation"
```

---

## Task 7: Hotspot Detection

**Files:**
- Create: `pipeline/analysis/hotspots.py`

- [ ] **Step 1: Write implementation**

```python
# pipeline/analysis/hotspots.py
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
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/analysis/hotspots.py
git commit -m "feat: add deforestation hotspot detection"
```

---

## Task 8: Run All Tests

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass.

- [ ] **Step 2: Final commit if needed**

```bash
git add -A
git commit -m "fix: address any test failures from Plan 2"
```

---

## Summary

| Module | Status | Tests |
|--------|--------|-------|
| `pipeline/classification/base.py` | BaseClassifier ABC | — |
| `pipeline/classification/ensemble.py` | RF+XGB+SVM ensemble | `test_classification.py` |
| `pipeline/classification/postprocess.py` | Mode filter, MMU, water | `test_postprocess.py` |
| `pipeline/classification/validation.py` | Metrics, spatial CV, temporal | `test_validation.py` |
| `pipeline/analysis/change_detection.py` | NDVI diff, transitions | `test_change_detection.py` |
| `pipeline/analysis/statistics.py` | Zonal stats, yearly summary | `test_statistics.py` |
| `pipeline/analysis/hotspots.py` | Cumulative loss hotspots | — |

**Next plan:** `2026-03-23-cwbverde-plan-3-events.md` (Events System)
