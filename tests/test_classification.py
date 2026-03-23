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

    # Shuffle so that train/test splits contain all classes
    idx = rng.permutation(len(y))
    return X[idx], y[idx]


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
