"""
ThermaCity - Fast Heuristic Explainability Service (No OOM)
"""
import logging
from typing import Any
import numpy as np

logger = logging.getLogger(__name__)

_FEATURE_LABELS = {
    'ndvi': 'Vegetation Cover (NDVI)',
    'ndbi': 'Urban Density (NDBI)',
    'ndwi': 'Water Presence (NDWI)',
    'tree_canopy_frac': 'Tree Canopy Coverage'
}

_FEATURE_DESCRIPTIONS = {
    'ndvi': {'positive': 'Low vegetation increases surface heat', 'negative': 'Good vegetation cover provides cooling'},
    'ndbi': {'positive': 'Dense built-up area absorbs heat', 'negative': 'Lower built-up density reduces heat'},
    'ndwi': {'positive': 'Lack of water reduces evaporative cooling', 'negative': 'Water bodies provide cooling'},
    'tree_canopy_frac': {'positive': 'Sparse canopy fails to provide shade', 'negative': 'Dense canopy provides shade cooling'}
}

class Explainer:
    def __init__(self, ml_predictor):
        self._predictor = ml_predictor
        self._feature_names = ml_predictor.get_feature_names()
        self._model = None
        self._init_explainer()

    def _init_explainer(self):
        try:
            pipeline = self._predictor._pipeline
            if hasattr(pipeline, 'named_steps'):
                self._model = pipeline.named_steps.get('randomforestregressor', pipeline.named_steps.get('regressor', pipeline[-1]))
            elif hasattr(pipeline, 'steps'):
                self._model = pipeline.steps[-1][1]
            else:
                self._model = pipeline
            logger.info('Heuristic explainer initialized')
        except Exception as e:
            logger.warning('Failed to init explainer: %s', e)
            self._model = None

    def explain_cell(self, features: dict[str, Any]) -> dict[str, Any]:
        if self._model is None:
            return {'error': 'Explainer not available'}
        try:
            predicted = self._predictor.predict_lst(features)
            base_value = 39.5
            total_diff = predicted - base_value
            importances = getattr(self._model, 'feature_importances_', [0.25, 0.25, 0.25, 0.25])
            means = {'ndvi': 0.15, 'ndbi': 0.25, 'ndwi': 0.05, 'tree_canopy_frac': 0.15}
            weights = []
            for i, feat_name in enumerate(self._feature_names):
                val = float(features.get(feat_name, means.get(feat_name, 0)))
                mean = means.get(feat_name, 0)
                imp = importances[i] if i < len(importances) else 0.25
                dev = (val - mean) * imp
                if feat_name in ['ndvi', 'ndwi', 'tree_canopy_frac']:
                    raw_impact = -dev
                else:
                    raw_impact = dev
                weights.append((feat_name, raw_impact))

            sum_abs_weights = sum(abs(w[1]) for w in weights)
            contributions = []
            for feat_name, raw_impact in weights:
                if sum_abs_weights > 0.0001:
                    impact = (raw_impact / sum_abs_weights) * abs(total_diff)
                    impact = -abs(impact) if raw_impact < 0 else abs(impact)
                else:
                    impact = 0.0
                direction = 'heating' if impact > 0 else 'cooling'
                desc_key = 'positive' if impact > 0 else 'negative'
                contributions.append({
                    'feature': feat_name,
                    'label': _FEATURE_LABELS.get(feat_name, feat_name),
                    'value': round(float(features.get(feat_name, 0)), 4),
                    'impact': round(impact, 2),
                    'impact_pct': round(abs(impact) / max(abs(total_diff), 0.01) * 100, 1),
                    'direction': direction,
                    'description': _FEATURE_DESCRIPTIONS.get(feat_name, {}).get(desc_key, '')
                })
            contributions.sort(key=lambda c: abs(c['impact']), reverse=True)
            return {'base_value': round(base_value, 2), 'predicted_value': round(predicted, 2), 'contributions': contributions}
        except Exception as e:
            logger.error('Explanation failed: %s', e)
            return {'error': str(e)}
