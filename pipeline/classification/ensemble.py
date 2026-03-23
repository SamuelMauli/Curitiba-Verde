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
