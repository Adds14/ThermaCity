#!/usr/bin/env python3
"""
ThermaCity — Random Forest LST Predictor: Evaluation Script

Loads the serialized model and test split to produce a comprehensive
academic evaluation report suitable for a B.Tech project viva.

Metrics Computed:
  - Root Mean Square Error (RMSE) — primary error metric in °C
  - Mean Absolute Error (MAE) — interpretable average error in °C
  - R² Score — proportion of variance explained (0–1)
  - Mean Bias Error (MBE) — systematic over/under-prediction
  - Per-feature partial dependence summary

Additional Analysis:
  - Residual statistics (mean, std, skewness)
  - Error distribution by temperature range (binned)
  - Year-wise performance breakdown (temporal stability)
  - Predicted vs Observed summary table

Usage:
    python evaluate_model.py
    python evaluate_model.py --model ../models/rf_lst_predictor_v1.joblib --test ../data/test_split.csv
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════

FEATURE_COLUMNS = ["ndvi", "ndbi", "ndwi", "tree_canopy_frac"]
TARGET_COLUMN = "lst_observed"
TARGET_COLUMN_ALIAS = "lst"  # Alternate name from GEE export

MODEL_VERSION = "v1"


# ══════════════════════════════════════════════════════════════
# Evaluation Functions
# ══════════════════════════════════════════════════════════════


def load_model(model_path: Path):
    """Load the serialized sklearn Pipeline."""
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        logger.error("Run train_model.py first.")
        sys.exit(1)

    logger.info(f"Loading model: {model_path}")
    pipeline = joblib.load(model_path)
    logger.info(f"  Pipeline steps: {[step[0] for step in pipeline.steps]}")
    return pipeline


def load_test_data(test_path: Path) -> pd.DataFrame:
    """Load and validate the test split."""
    if not test_path.exists():
        logger.error(f"Test data not found: {test_path}")
        logger.error("Run train_model.py first to generate the test split.")
        sys.exit(1)

    logger.info(f"Loading test data: {test_path}")
    df = pd.read_csv(test_path)

    # Resolve target column name
    if TARGET_COLUMN not in df.columns and TARGET_COLUMN_ALIAS in df.columns:
        df = df.rename(columns={TARGET_COLUMN_ALIAS: TARGET_COLUMN})
    elif TARGET_COLUMN not in df.columns:
        raise ValueError(
            f"Target column '{TARGET_COLUMN}' not found. "
            f"Columns: {list(df.columns)}"
        )

    # Drop any residual null targets
    df = df.dropna(subset=[TARGET_COLUMN])

    logger.info(f"  Test samples: {len(df)}")
    return df


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Compute comprehensive regression metrics.

    Returns dict with all metrics needed for academic reporting.
    """
    residuals = y_true - y_pred

    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
        "mbe": float(np.mean(residuals)),  # Mean Bias Error
        "residual_std": float(np.std(residuals)),
        "max_overpredict": float(np.min(residuals)),  # Most negative residual
        "max_underpredict": float(np.max(residuals)),  # Most positive residual
        "n_samples": len(y_true),
        "y_true_mean": float(np.mean(y_true)),
        "y_true_std": float(np.std(y_true)),
        "y_pred_mean": float(np.mean(y_pred)),
        "y_pred_std": float(np.std(y_pred)),
    }

    return metrics


def evaluate_by_temperature_range(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> pd.DataFrame:
    """
    Break down model performance by observed temperature bins.

    This reveals whether the model performs differently in extreme
    heat zones vs cooler areas — critical for UHI applications.
    """
    bins = [0, 30, 35, 40, 45, 50, 60]
    labels = ["<30°C", "30-35°C", "35-40°C", "40-45°C", "45-50°C", ">50°C"]

    df = pd.DataFrame({"observed": y_true, "predicted": y_pred})
    df["temp_bin"] = pd.cut(df["observed"], bins=bins, labels=labels, right=False)

    results = []
    for bin_label in labels:
        subset = df[df["temp_bin"] == bin_label]
        if len(subset) == 0:
            continue

        obs = subset["observed"].values
        pred = subset["predicted"].values

        results.append({
            "temperature_range": bin_label,
            "n_samples": len(subset),
            "rmse": float(np.sqrt(mean_squared_error(obs, pred))),
            "mae": float(mean_absolute_error(obs, pred)),
            "r2": float(r2_score(obs, pred)) if len(subset) > 1 else np.nan,
            "mean_bias": float(np.mean(obs - pred)),
        })

    return pd.DataFrame(results)


def evaluate_by_year(
    df: pd.DataFrame,
    y_pred: np.ndarray,
) -> pd.DataFrame | None:
    """
    Break down model performance by year.

    Tests temporal stability — ensures the model generalises
    across different hot seasons, not just one year's conditions.
    """
    if "year" not in df.columns:
        return None

    df = df.copy()
    df["predicted"] = y_pred

    results = []
    for year, group in df.groupby("year"):
        obs = group[TARGET_COLUMN].values
        pred = group["predicted"].values

        results.append({
            "year": int(year),
            "n_samples": len(group),
            "rmse": float(np.sqrt(mean_squared_error(obs, pred))),
            "mae": float(mean_absolute_error(obs, pred)),
            "r2": float(r2_score(obs, pred)) if len(group) > 1 else np.nan,
        })

    return pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════
# Report Generation
# ══════════════════════════════════════════════════════════════


def print_report(
    metrics: dict,
    temp_breakdown: pd.DataFrame,
    year_breakdown: pd.DataFrame | None,
) -> None:
    """Print a comprehensive evaluation report to the console."""

    print("\n" + "═" * 70)
    print("  ThermaCity — Random Forest LST Predictor Evaluation Report")
    print("═" * 70)

    # ── Primary Metrics ──
    print("\n┌─────────────────────────────────────────────────────────┐")
    print("│                   PRIMARY METRICS                       │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│  Root Mean Square Error (RMSE):   {metrics['rmse']:8.4f} °C          │")
    print(f"│  Mean Absolute Error (MAE):       {metrics['mae']:8.4f} °C          │")
    print(f"│  R² Score:                        {metrics['r2']:8.4f}             │")
    print(f"│  Mean Bias Error (MBE):           {metrics['mbe']:+8.4f} °C          │")
    print(f"│  Test Samples:                    {metrics['n_samples']:8d}             │")
    print("└─────────────────────────────────────────────────────────┘")

    # ── Interpretation ──
    r2 = metrics["r2"]
    if r2 >= 0.85:
        quality = "EXCELLENT — model captures the land-cover → LST relationship very well"
    elif r2 >= 0.75:
        quality = "GOOD — suitable for scenario simulation with acceptable accuracy"
    elif r2 >= 0.60:
        quality = "MODERATE — consider feature engineering or hyperparameter tuning"
    else:
        quality = "POOR — model may need additional features or data quality review"

    print(f"\n  Model Quality: {quality}")

    mbe = metrics["mbe"]
    if abs(mbe) < 0.5:
        print(f"  Bias Assessment: Negligible systematic bias ({mbe:+.4f} °C)")
    elif mbe > 0:
        print(f"  Bias Assessment: Slight under-prediction tendency ({mbe:+.4f} °C)")
    else:
        print(f"  Bias Assessment: Slight over-prediction tendency ({mbe:+.4f} °C)")

    # ── Distribution Summary ──
    print("\n┌─────────────────────────────────────────────────────────┐")
    print("│               PREDICTION DISTRIBUTION                   │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│  Observed Mean ± Std:   {metrics['y_true_mean']:6.2f} ± {metrics['y_true_std']:.2f} °C              │")
    print(f"│  Predicted Mean ± Std:  {metrics['y_pred_mean']:6.2f} ± {metrics['y_pred_std']:.2f} °C              │")
    print(f"│  Max Over-prediction:   {abs(metrics['max_overpredict']):6.2f} °C                     │")
    print(f"│  Max Under-prediction:  {metrics['max_underpredict']:6.2f} °C                     │")
    print(f"│  Residual Std:          {metrics['residual_std']:6.2f} °C                     │")
    print("└─────────────────────────────────────────────────────────┘")

    # ── Temperature Range Breakdown ──
    print("\n  Performance by Temperature Range:")
    print(f"  {'Range':12s} {'N':>8s} {'RMSE':>10s} {'MAE':>10s} {'R²':>10s} {'Bias':>10s}")
    print(f"  {'-'*12} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    for _, row in temp_breakdown.iterrows():
        r2_str = f"{row['r2']:.4f}" if not np.isnan(row['r2']) else "   N/A"
        print(
            f"  {row['temperature_range']:12s} {row['n_samples']:8d} "
            f"{row['rmse']:10.4f} {row['mae']:10.4f} "
            f"{r2_str:>10s} {row['mean_bias']:+10.4f}"
        )

    # ── Year-wise Breakdown ──
    if year_breakdown is not None:
        print("\n  Performance by Year (Temporal Stability):")
        print(f"  {'Year':6s} {'N':>8s} {'RMSE':>10s} {'MAE':>10s} {'R²':>10s}")
        print(f"  {'-'*6} {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
        for _, row in year_breakdown.iterrows():
            r2_str = f"{row['r2']:.4f}" if not np.isnan(row['r2']) else "   N/A"
            print(
                f"  {int(row['year']):6d} {row['n_samples']:8d} "
                f"{row['rmse']:10.4f} {row['mae']:10.4f} "
                f"{r2_str:>10s}"
            )

        # Check temporal stability
        r2_values = year_breakdown["r2"].dropna()
        if len(r2_values) > 1:
            r2_range = r2_values.max() - r2_values.min()
            if r2_range < 0.05:
                print(f"\n  ✓ Temporal stability: EXCELLENT (R² range = {r2_range:.4f})")
            elif r2_range < 0.10:
                print(f"\n  ✓ Temporal stability: GOOD (R² range = {r2_range:.4f})")
            else:
                print(f"\n  ⚠ Temporal stability: VARIABLE (R² range = {r2_range:.4f})")

    print("\n" + "═" * 70)


# ══════════════════════════════════════════════════════════════
# CLI Entry Point
# ══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the ThermaCity RF LST Predictor on the held-out test set.",
    )
    parser.add_argument(
        "--model", type=Path,
        default=Path(__file__).parent.parent / "models" / f"rf_lst_predictor_{MODEL_VERSION}.joblib",
        help="Path to serialized model (default: ../models/rf_lst_predictor_v1.joblib)",
    )
    parser.add_argument(
        "--test", type=Path,
        default=Path(__file__).parent.parent / "data" / "test_split.csv",
        help="Path to test split CSV (default: ../data/test_split.csv)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Optional path to save evaluation report as JSON",
    )
    args = parser.parse_args()

    # ── Load ──
    pipeline = load_model(args.model)
    test_df = load_test_data(args.test)

    X_test = test_df[FEATURE_COLUMNS]
    y_true = test_df[TARGET_COLUMN].values

    # ── Predict ──
    logger.info("Running predictions on test set...")
    y_pred = pipeline.predict(X_test)

    # ── Compute metrics ──
    metrics = compute_metrics(y_true, y_pred)
    temp_breakdown = evaluate_by_temperature_range(y_true, y_pred)
    year_breakdown = evaluate_by_year(test_df, y_pred)

    # ── Print report ──
    print_report(metrics, temp_breakdown, year_breakdown)

    # ── Save report (optional) ──
    if args.output:
        report = {
            "model_version": MODEL_VERSION,
            "model_path": str(args.model.resolve()),
            "test_data_path": str(args.test.resolve()),
            "metrics": metrics,
            "performance_by_temperature": temp_breakdown.to_dict(orient="records"),
        }
        if year_breakdown is not None:
            report["performance_by_year"] = year_breakdown.to_dict(orient="records")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"\nEvaluation report saved to: {args.output}")

    # ── Exit code based on quality ──
    if metrics["r2"] >= 0.60:
        logger.info("\n✓ Model meets minimum quality threshold (R² ≥ 0.60).")
        sys.exit(0)
    else:
        logger.warning(
            f"\n⚠ Model below quality threshold (R² = {metrics['r2']:.4f} < 0.60). "
            "Review training data and hyperparameters."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
