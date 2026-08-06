"""
ThermaCity — Heat Vulnerability Index Calculator

Computes the Heat Vulnerability Index (HVI) from environmental and
demographic inputs using a weighted, min-max normalised formula.

HVI formula (0–100 scale)
─────────────────────────
    HVI = w_lst        × norm(LST_predicted)
        + w_population × norm(PopulationDensity)
        + w_canopy     × norm(1 − TreeCanopyFrac)
        + w_humidity   × norm(Humidity)
        + w_wind       × norm(1 / WindSpeed)

Tier thresholds:
    Heat-Safe   0–25  |  Caution  26–50  |  Stressed  51–75  |  Emergency  76–100
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Default weights — mirrors config.Settings.hvi_weight_dict
_DEFAULT_WEIGHTS: dict[str, float] = {
    "lst": 0.35,
    "humidity": 0.15,
    "wind": 0.10,
    "population": 0.20,
    "canopy": 0.20,
}

# Tier boundaries (inclusive lower, exclusive upper — except Emergency).
_TIERS: list[tuple[float, float, str]] = [
    (0.0, 26.0, "Heat-Safe"),
    (26.0, 51.0, "Caution"),
    (51.0, 76.0, "Stressed"),
    (76.0, 101.0, "Emergency"),
]


class HVICalculator:
    """Stateless calculator for the Heat Vulnerability Index.

    All methods are pure functions — no instance state is required.
    The class groups them under a single namespace for clarity.
    """

    # ── public API ────────────────────────────────────────────

    @staticmethod
    def compute_single(
        lst: float,
        humidity: float,
        wind_speed: float,
        population_density: float,
        tree_canopy_frac: float,
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Compute HVI for **one** cell without cross-cell normalisation.

        Because normalisation requires a population of values, the raw
        inputs are assumed to be *pre-normalised* to [0, 1] when calling
        this method.  For batch processing with automatic normalisation
        use :meth:`compute_batch`.

        Parameters
        ----------
        lst, humidity, wind_speed, population_density, tree_canopy_frac
            Normalised component values in [0, 1].
        weights : dict, optional
            Override the default weight dict.

        Returns
        -------
        dict
            ``{"hvi_score": float, "hvi_tier": str}``
        """
        w = weights or _DEFAULT_WEIGHTS

        hvi_score = (
            w["lst"] * lst
            + w["humidity"] * humidity
            + w["wind"] * wind_speed        # caller passes norm(1/ws)
            + w["population"] * population_density
            + w["canopy"] * tree_canopy_frac  # caller passes norm(1 - frac)
        ) * 100.0

        hvi_score = float(np.clip(hvi_score, 0.0, 100.0))
        hvi_tier = HVICalculator._assign_tier(hvi_score)

        return {"hvi_score": round(hvi_score, 2), "hvi_tier": hvi_tier}

    @staticmethod
    def compute_batch(
        rows: list[dict[str, Any]],
        weights: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Compute HVI for **multiple** cells with min-max normalisation.

        Each element of *rows* must contain at least the keys:
        ``lst_predicted``, ``humidity``, ``wind_speed``,
        ``population_density``, ``tree_canopy_frac``.

        Normalisation is performed **across the batch** so that the
        minimum value maps to 0 and the maximum maps to 1.

        Parameters
        ----------
        rows : list[dict]
            Raw (un-normalised) feature dicts for every cell in a year.
        weights : dict, optional
            Override the default weight dict.

        Returns
        -------
        list[dict]
            One ``{"hvi_score": float, "hvi_tier": str}`` per input row.
        """
        if not rows:
            return []

        w = weights or _DEFAULT_WEIGHTS
        n = len(rows)

        # ── extract raw arrays ────────────────────────────────
        lst_arr = np.array(
            [r.get("lst_predicted", np.nan) for r in rows], dtype=np.float64
        )
        pop_arr = np.array(
            [r.get("population_density", np.nan) for r in rows], dtype=np.float64
        )
        canopy_arr = np.array(
            [r.get("tree_canopy_frac", np.nan) for r in rows], dtype=np.float64
        )
        humidity_arr = np.array(
            [r.get("humidity", np.nan) for r in rows], dtype=np.float64
        )
        wind_arr = np.array(
            [r.get("wind_speed", np.nan) for r in rows], dtype=np.float64
        )

        # ── transform components ──────────────────────────────
        # Canopy deficit: higher tree cover → lower vulnerability
        canopy_deficit = 1.0 - np.nan_to_num(canopy_arr, nan=0.5)

        # Wind stagnation: calm air traps heat
        # Guard against zero division; treat zero/missing wind as very calm.
        safe_wind = np.where(
            (wind_arr <= 0) | np.isnan(wind_arr), 0.01, wind_arr
        )
        wind_stagnation = 1.0 / safe_wind

        # ── normalise each component (min-max, 0 → 1) ────────
        norm_lst = HVICalculator._normalize(lst_arr)
        norm_pop = HVICalculator._normalize(pop_arr)
        norm_canopy = HVICalculator._normalize(canopy_deficit)
        norm_humidity = HVICalculator._normalize(humidity_arr)
        norm_wind = HVICalculator._normalize(wind_stagnation)

        # ── weighted sum → 0-100 scale ────────────────────────
        hvi = (
            w["lst"] * norm_lst
            + w["population"] * norm_pop
            + w["canopy"] * norm_canopy
            + w["humidity"] * norm_humidity
            + w["wind"] * norm_wind
        ) * 100.0

        hvi = np.clip(hvi, 0.0, 100.0)

        logger.info(
            "compute_batch  n=%d, HVI range=[%.2f, %.2f], mean=%.2f",
            n,
            float(np.nanmin(hvi)),
            float(np.nanmax(hvi)),
            float(np.nanmean(hvi)),
        )

        results: list[dict[str, Any]] = []
        for score in hvi:
            score_val = round(float(score), 2)
            results.append(
                {
                    "hvi_score": score_val,
                    "hvi_tier": HVICalculator._assign_tier(score_val),
                }
            )
        return results

    # ── internal helpers ──────────────────────────────────────

    @staticmethod
    def _assign_tier(score: float) -> str:
        """Map a 0–100 HVI score to the corresponding vulnerability tier.

        Tier boundaries
        ───────────────
        Heat-Safe   [0, 25]
        Caution     [26, 50]
        Stressed    [51, 75]
        Emergency   [76, 100]
        """
        for lo, hi, tier in _TIERS:
            if lo <= score < hi:
                return tier
        # Fallback — should never happen after np.clip
        return "Emergency"

    @staticmethod
    def _normalize(values: NDArray[np.float64]) -> NDArray[np.float64]:
        """Min-max normalisation to [0, 1].

        If all values are identical (max == min), returns an array of
        zeros to avoid division by zero.  ``NaN`` values are propagated.
        """
        v_min = float(np.nanmin(values))
        v_max = float(np.nanmax(values))
        if v_max - v_min < 1e-12:
            # Constant array → normalised to 0.0
            return np.where(np.isnan(values), np.nan, 0.0)
        return (values - v_min) / (v_max - v_min)
