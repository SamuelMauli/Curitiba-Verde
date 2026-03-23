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
