"""
ThermaCity — ML Predictor Service

Loads a pre-trained scikit-learn Pipeline (SimpleImputer → RandomForestRegressor)
from a joblib file and exposes methods to predict Land Surface Temperature (LST)
from satellite-derived spectral indices.

Features expected by the model:
    ndvi, ndbi, ndwi, tree_canopy_frac  →  LST (°C)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# Canonical feature order the model was trained on.
_MODEL_FEATURES: list[str] = ["ndvi", "ndbi", "ndwi", "tree_canopy_frac"]


class MLPredictor:
    """Wrapper around the serialised sklearn LST prediction pipeline.

    Parameters
    ----------
    model_path : str | Path
        Absolute or relative path to the ``.joblib`` model file.

    Raises
    ------
    FileNotFoundError
        If *model_path* does not point to an existing file.
    """

    def __init__(self, model_path: str | Path) -> None:
        self._model_path = Path(model_path)
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"ML model file not found: {self._model_path.resolve()}"
            )

        logger.info("Loading ML model from %s …", self._model_path)
        self._pipeline = joblib.load(self._model_path)
        logger.info("ML model loaded successfully.")

    # ── public API ────────────────────────────────────────────

    def predict_lst(self, features: dict[str, Any]) -> float:
        """Predict LST for a **single** grid cell.

        Parameters
        ----------
        features : dict
            Mapping of feature name → value.  Missing keys are passed as
            ``np.nan`` so the pipeline's ``SimpleImputer`` can handle them.

        Returns
        -------
        float
            Predicted Land Surface Temperature in °C.
        """
        row = self._features_to_array(features)
        prediction: float = float(self._pipeline.predict(row)[0])
        logger.debug("predict_lst  features=%s → %.2f °C", features, prediction)
        return prediction

    def predict_batch(
        self, features_list: list[dict[str, Any]]
    ) -> list[float]:
        """Predict LST for **multiple** grid cells in one call.

        Parameters
        ----------
        features_list : list[dict]
            Each element is a feature dict (same schema as
            :meth:`predict_lst`).

        Returns
        -------
        list[float]
            One predicted LST value per input row, in the same order.
        """
        if not features_list:
            return []

        matrix = np.vstack(
            [self._features_to_array(f) for f in features_list]
        )
        predictions: list[float] = self._pipeline.predict(matrix).tolist()
        logger.info(
            "predict_batch  n=%d, LST range=[%.2f, %.2f]",
            len(predictions),
            min(predictions),
            max(predictions),
        )
        return predictions

    @staticmethod
    def get_feature_names() -> list[str]:
        """Return the ordered list of feature names the model expects."""
        return list(_MODEL_FEATURES)

    # ── internals ─────────────────────────────────────────────

    def _features_to_array(self, features: dict[str, Any]) -> np.ndarray:
        """Convert a feature dict to a 2-D numpy array (1 × n_features).

        Missing keys are filled with ``np.nan`` — the pipeline's
        ``SimpleImputer`` stage replaces them with training-set medians.
        """
        row = [features.get(name, np.nan) for name in _MODEL_FEATURES]
        return np.array(row, dtype=np.float64).reshape(1, -1)

    def __repr__(self) -> str:
        return f"<MLPredictor model={self._model_path.name!r}>"
