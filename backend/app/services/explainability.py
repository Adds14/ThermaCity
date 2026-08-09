"""
ThermaCity — SHAP Explainability Service

Provides human-readable explanations for why a specific grid cell
has its predicted temperature and vulnerability score, using
SHapley Additive exPlanations (SHAP) for the Random Forest model.
"""

import logging
from typing import Any

import numpy as np
import shap

logger = logging.getLogger(__name__)

# Human-readable labels for each feature
_FEATURE_LABELS = {
    "ndvi": "Vegetation Cover (NDVI)",
    "ndbi": "Urban Density (NDBI)",
    "ndwi": "Water Presence (NDWI)",
    "tree_canopy_frac": "Tree Canopy Coverage",
}

_FEATURE_DESCRIPTIONS = {
    "ndvi": {
        "positive": "Low vegetation in this area increases surface temperature",
        "negative": "Good vegetation cover helps cool this area",
    },
    "ndbi": {
        "positive": "Dense concrete/asphalt absorbs and re-emits heat",
        "negative": "Lower built-up density reduces heat absorption",
    },
    "ndwi": {
        "positive": "Lack of water bodies removes evaporative cooling",
        "negative": "Nearby water bodies provide evaporative cooling",
    },
    "tree_canopy_frac": {
        "positive": "Sparse tree canopy fails to provide shade",
        "negative": "Dense tree canopy provides effective shade cooling",
    },
}


class Explainer:
    """SHAP-based explainability for LST predictions."""

    def __init__(self, ml_predictor):
        """
        Parameters
        ----------
        ml_predictor : MLPredictor
            The loaded ML predictor instance.
        """
        self._predictor = ml_predictor
        self._explainer = None
        self._feature_names = ml_predictor.get_feature_names()
        self._init_explainer()

    def _init_explainer(self):
        """Initialize SHAP TreeExplainer from the Random Forest pipeline."""
        try:
            pipeline = self._predictor._pipeline
            # Extract the RandomForest step from the pipeline
            if hasattr(pipeline, 'named_steps'):
                model = pipeline.named_steps.get('randomforestregressor',
                         pipeline.named_steps.get('regressor', pipeline[-1]))
            elif hasattr(pipeline, 'steps'):
                model = pipeline.steps[-1][1]
            else:
                model = pipeline

            self._explainer = shap.TreeExplainer(model)
            logger.info("SHAP TreeExplainer initialized successfully.")
        except Exception as e:
            logger.warning("Failed to initialize SHAP explainer: %s", e)
            self._explainer = None

    def explain_cell(self, features: dict[str, Any]) -> dict[str, Any]:
        """Explain why a cell has its predicted LST.

        Parameters
        ----------
        features : dict
            Feature dict with keys: ndvi, ndbi, ndwi, tree_canopy_frac

        Returns
        -------
        dict
            {
                "base_value": float (expected LST across training set),
                "predicted_value": float,
                "contributions": [
                    {
                        "feature": str,
                        "label": str,
                        "value": float (actual feature value),
                        "impact": float (SHAP value in °C),
                        "direction": "heating" | "cooling",
                        "description": str
                    }
                ]
            }
        """
        if self._explainer is None:
            return {"error": "SHAP explainer not available"}

        try:
            # Prepare feature array
            row = np.array(
                [features.get(f, np.nan) for f in self._feature_names],
                dtype=np.float64
            ).reshape(1, -1)

            # Handle imputation if the pipeline has an imputer
            pipeline = self._predictor._pipeline
            if hasattr(pipeline, 'named_steps') and 'simpleimputer' in pipeline.named_steps:
                row = pipeline.named_steps['simpleimputer'].transform(row)

            # Compute SHAP values
            shap_values = self._explainer.shap_values(row)

            # shap_values shape: (1, n_features) for regression
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            sv = shap_values[0]  # first (only) sample

            base_value = float(self._explainer.expected_value)
            if isinstance(self._explainer.expected_value, np.ndarray):
                base_value = float(self._explainer.expected_value[0])

            predicted = self._predictor.predict_lst(features)

            # Build contributions sorted by absolute impact
            contributions = []
            for i, feat_name in enumerate(self._feature_names):
                impact = float(sv[i])
                direction = "heating" if impact > 0 else "cooling"
                desc_key = "positive" if impact > 0 else "negative"

                contributions.append({
                    "feature": feat_name,
                    "label": _FEATURE_LABELS.get(feat_name, feat_name),
                    "value": round(float(features.get(feat_name, 0)), 4),
                    "impact": round(impact, 2),
                    "impact_pct": round(abs(impact) / max(abs(predicted - base_value), 0.01) * 100, 1),
                    "direction": direction,
                    "description": _FEATURE_DESCRIPTIONS.get(feat_name, {}).get(desc_key, ""),
                })

            # Sort by absolute impact (most important first)
            contributions.sort(key=lambda c: abs(c["impact"]), reverse=True)

            return {
                "base_value": round(base_value, 2),
                "predicted_value": round(predicted, 2),
                "contributions": contributions,
            }
        except Exception as e:
            logger.error("SHAP explanation failed: %s", e)
            return {"error": str(e)}
