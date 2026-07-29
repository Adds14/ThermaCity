#!/usr/bin/env python3
"""
ThermaCity — Random Forest LST Predictor: Training Pipeline

Trains a Random Forest Regressor to learn the physical relationship
between land-cover characteristics and observed Land Surface Temperature.

Model Scope (CRITICAL DESIGN CONSTRAINT):
  The model predicts LST from land-cover features ONLY. It does NOT
  predict vulnerability. The HVI is computed deterministically downstream
  by combining the model's LST predictions with humidity, wind, and
  population data. This separation ensures:
    1. The ML component is scientifically interpretable.
    2. The frontend scenario simulator can modify land-cover inputs
       (e.g., "add 20% more trees") and get a physically meaningful
       temperature prediction without conflating it with demographics.

Feature Matrix:
  X = [ndvi, ndbi, ndwi, tree_canopy_frac]
  y = lst_observed (Landsat hot-season median, °C)

Pipeline Architecture:
  1. Load merged training_set.csv
  2. Drop rows with null targets (lst_observed) — non-negotiable
  3. Impute remaining NaN features with median (robust to outliers)
  4. 80/20 train/test split (stratified by year for temporal balance)
  5. Train RandomForestRegressor inside a sklearn Pipeline
  6. Evaluate on test set (RMSE, MAE, R²)
  7. Export feature importances → JSON
  8. Serialize model → joblib
  9. Save train/test splits → CSV

Usage:
    python train_model.py --input ../data/training_set.csv

Output:
    ../models/rf_lst_predictor_v1.joblib     — Serialized sklearn Pipeline
    ../models/feature_importance_v1.json     — Feature importance scores
    ../data/train_split.csv                  — Training data (for reproducibility)
    ../data/test_split.csv                   — Test data (for evaluate_model.py)
    ../models/training_report_v1.json        — Training metadata & metrics
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════

# Feature columns — ONLY land-cover variables that physically
# influence surface temperature. Demographics and climate exposure
# indicators are intentionally excluded (they feed the HVI formula).
FEATURE_COLUMNS = ["ndvi", "ndbi", "ndwi", "tree_canopy_frac"]

# Target column — in the merged CSV this is 'lst' (from GEE export).
# In the PostGIS schema it maps to 'lst_observed'.
TARGET_COLUMN = "lst"
TARGET_COLUMN_ALIAS = "lst_observed"  # Alternative name the user may use

# Random Forest hyperparameters
RF_PARAMS = {
    "n_estimators": 200,
    "max_depth": 15,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "max_features": "sqrt",
    "n_jobs": -1,           # Use all available CPU cores
    "random_state": 42,
    "verbose": 1,
}

# Train/test split
TEST_SIZE = 0.20
SPLIT_RANDOM_STATE = 42

# Model version tag (increment when retraining)
MODEL_VERSION = "v1"


# ══════════════════════════════════════════════════════════════
# Data Loading & Preprocessing
# ══════════════════════════════════════════════════════════════


def load_and_validate_data(csv_path: Path) -> pd.DataFrame:
    """
    Load the merged training CSV and perform pre-training validation.

    Critical Steps:
      1. Resolve target column name (lst vs lst_observed)
      2. Drop rows with null targets (MANDATORY — cannot train on missing y)
      3. Report feature-level statistics

    Returns:
        Cleaned DataFrame with confirmed feature and target columns.

    Raises:
        ValueError if required columns are missing.
    """
    logger.info(f"Loading dataset: {csv_path}")
    df = pd.read_csv(csv_path)

    logger.info(f"  Raw shape: {df.shape[0]} rows × {df.shape[1]} columns")
    logger.info(f"  Columns: {list(df.columns)}")

    # ── Resolve target column name ──
    if TARGET_COLUMN in df.columns:
        target_col = TARGET_COLUMN
    elif TARGET_COLUMN_ALIAS in df.columns:
        target_col = TARGET_COLUMN_ALIAS
        logger.info(f"  Using '{TARGET_COLUMN_ALIAS}' as target (aliased from '{TARGET_COLUMN}')")
    else:
        raise ValueError(
            f"Target column not found. Expected '{TARGET_COLUMN}' or "
            f"'{TARGET_COLUMN_ALIAS}' in columns: {list(df.columns)}"
        )

    # Normalize target column name to 'lst_observed' for clarity
    if target_col != TARGET_COLUMN_ALIAS:
        df = df.rename(columns={target_col: TARGET_COLUMN_ALIAS})

    # ── Validate feature columns exist ──
    missing_features = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing_features:
        raise ValueError(
            f"Missing feature columns: {missing_features}. "
            f"Available: {list(df.columns)}"
        )

    # ── DROP ROWS WITH NULL TARGETS — NON-NEGOTIABLE ──
    null_targets = df[TARGET_COLUMN_ALIAS].isna().sum()
    if null_targets > 0:
        logger.warning(
            f"  Dropping {null_targets} rows with null '{TARGET_COLUMN_ALIAS}' "
            f"({null_targets / len(df) * 100:.1f}% of data)"
        )
        df = df.dropna(subset=[TARGET_COLUMN_ALIAS])

    logger.info(f"  Clean shape: {df.shape[0]} rows × {df.shape[1]} columns")

    # ── Feature statistics ──
    logger.info("\n  Feature statistics (post-cleaning):")
    logger.info(f"  {'Column':25s} {'Count':>8s} {'Nulls':>8s} {'Mean':>10s} {'Std':>10s} {'Min':>10s} {'Max':>10s}")
    logger.info(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    for col in FEATURE_COLUMNS + [TARGET_COLUMN_ALIAS]:
        if col in df.columns:
            series = df[col]
            logger.info(
                f"  {col:25s} {series.count():8d} {series.isna().sum():8d} "
                f"{series.mean():10.4f} {series.std():10.4f} "
                f"{series.min():10.4f} {series.max():10.4f}"
            )

    # ── Year distribution ──
    if "year" in df.columns:
        logger.info(f"\n  Samples per year:")
        for year, count in df["year"].value_counts().sort_index().items():
            logger.info(f"    {year}: {count} rows")

    return df


# ══════════════════════════════════════════════════════════════
# Model Training
# ══════════════════════════════════════════════════════════════


def build_pipeline() -> Pipeline:
    """
    Build the sklearn training pipeline.

    Architecture:
      1. SimpleImputer(strategy='median')
         - Handles NaN values in feature columns (e.g., cloud-contaminated
           NDVI cells or missing tree canopy at boundary cells).
         - Median is robust to outliers (better than mean for skewed
           environmental data).

      2. RandomForestRegressor
         - Non-parametric ensemble that handles non-linear relationships
           between land cover and temperature.
         - Feature importances provide explainability for planners.
         - Resistant to overfitting when properly depth-limited.

    Returns:
        Unfitted sklearn Pipeline.
    """
    pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "regressor",
                RandomForestRegressor(**RF_PARAMS),
            ),
        ]
    )

    logger.info("Pipeline architecture:")
    logger.info(f"  Step 1: SimpleImputer(strategy='median')")
    logger.info(f"  Step 2: RandomForestRegressor(")
    for key, val in RF_PARAMS.items():
        logger.info(f"            {key}={val},")
    logger.info(f"          )")

    return pipeline


def train_model(
    df: pd.DataFrame,
) -> tuple[Pipeline, pd.DataFrame, pd.DataFrame, dict]:
    """
    Train the Random Forest pipeline on the provided data.

    Args:
        df: Cleaned DataFrame with feature and target columns.

    Returns:
        Tuple of (fitted_pipeline, train_df, test_df, metrics_dict).
    """
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN_ALIAS]

    logger.info(f"\nFeature matrix: X = {list(FEATURE_COLUMNS)}")
    logger.info(f"Target vector:  y = {TARGET_COLUMN_ALIAS}")
    logger.info(f"Total samples:  {len(X)}")

    # ── Train/Test Split ──
    # Stratify by year if available (ensures temporal balance in both sets)
    stratify_col = df["year"] if "year" in df.columns else None
    stratify_label = "stratified by year" if stratify_col is not None else "random"

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        random_state=SPLIT_RANDOM_STATE,
        stratify=stratify_col,
    )

    logger.info(
        f"Train/test split: {len(X_train)} train / {len(X_test)} test "
        f"({stratify_label}, test_size={TEST_SIZE})"
    )

    # Reconstruct full DataFrames for saving splits
    train_df = df.loc[X_train.index].copy()
    test_df = df.loc[X_test.index].copy()

    # ── Build & Train Pipeline ──
    pipeline = build_pipeline()

    logger.info("\nTraining Random Forest Regressor...")
    start_time = datetime.now(timezone.utc)

    pipeline.fit(X_train, y_train)

    train_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"Training completed in {train_time:.1f} seconds.")

    # ── Evaluate on BOTH sets ──
    y_train_pred = pipeline.predict(X_train)
    y_test_pred = pipeline.predict(X_test)

    train_metrics = _compute_metrics(y_train, y_train_pred, prefix="train")
    test_metrics = _compute_metrics(y_test, y_test_pred, prefix="test")

    metrics = {**train_metrics, **test_metrics, "training_time_seconds": train_time}

    # ── Log metrics ──
    logger.info("\n" + "=" * 60)
    logger.info("MODEL EVALUATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"  {'Metric':20s} {'Train':>12s} {'Test':>12s}")
    logger.info(f"  {'-'*20} {'-'*12} {'-'*12}")
    logger.info(
        f"  {'RMSE (°C)':20s} "
        f"{train_metrics['train_rmse']:12.4f} "
        f"{test_metrics['test_rmse']:12.4f}"
    )
    logger.info(
        f"  {'MAE (°C)':20s} "
        f"{train_metrics['train_mae']:12.4f} "
        f"{test_metrics['test_mae']:12.4f}"
    )
    logger.info(
        f"  {'R² Score':20s} "
        f"{train_metrics['train_r2']:12.4f} "
        f"{test_metrics['test_r2']:12.4f}"
    )
    logger.info("=" * 60)

    # ── Overfit check ──
    r2_gap = train_metrics["train_r2"] - test_metrics["test_r2"]
    if r2_gap > 0.10:
        logger.warning(
            f"  ⚠ Potential overfitting detected: "
            f"R² gap = {r2_gap:.4f} (train−test). "
            f"Consider reducing max_depth or increasing min_samples_leaf."
        )
    else:
        logger.info(f"  ✓ R² gap = {r2_gap:.4f} — no significant overfitting.")

    return pipeline, train_df, test_df, metrics


def _compute_metrics(y_true, y_pred, prefix: str) -> dict:
    """Compute RMSE, MAE, R² and return as a dict."""
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    return {
        f"{prefix}_rmse": rmse,
        f"{prefix}_mae": mae,
        f"{prefix}_r2": r2,
        f"{prefix}_n_samples": len(y_true),
    }


# ══════════════════════════════════════════════════════════════
# Feature Importance Export
# ══════════════════════════════════════════════════════════════


def extract_feature_importances(
    pipeline: Pipeline,
    output_path: Path,
) -> dict:
    """
    Extract and save Random Forest feature importances.

    The importances represent the mean decrease in impurity (Gini importance)
    across all trees. Higher values indicate that the feature contributes
    more to predicting LST — which directly tells planners WHICH land-cover
    variable to target for maximum cooling impact.

    Args:
        pipeline:    Fitted sklearn Pipeline.
        output_path: Path to save the JSON file.

    Returns:
        Dict mapping feature names to importance scores.
    """
    # Access the regressor step from the pipeline
    regressor = pipeline.named_steps["regressor"]
    importances = regressor.feature_importances_

    # Pair with feature names and sort descending
    importance_dict = {
        name: float(score)
        for name, score in zip(FEATURE_COLUMNS, importances)
    }
    importance_sorted = dict(
        sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
    )

    # Log results
    logger.info("\nFeature Importances (Gini, descending):")
    logger.info(f"  {'Feature':25s} {'Importance':>12s} {'Bar':>30s}")
    logger.info(f"  {'-'*25} {'-'*12} {'-'*30}")
    max_imp = max(importance_sorted.values()) if importance_sorted else 1

    for name, score in importance_sorted.items():
        bar_len = int((score / max_imp) * 28)
        bar = "█" * bar_len
        logger.info(f"  {name:25s} {score:12.6f} {bar}")

    # Save to JSON
    export_data = {
        "model_version": MODEL_VERSION,
        "feature_importances": importance_sorted,
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN_ALIAS,
        "note": (
            "Gini importance — measures mean decrease in impurity. "
            "Higher = stronger influence on predicted LST."
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)

    logger.info(f"\n  Feature importances saved to: {output_path}")

    return importance_sorted


# ══════════════════════════════════════════════════════════════
# Artifact Serialization
# ══════════════════════════════════════════════════════════════


def save_artifacts(
    pipeline: Pipeline,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    metrics: dict,
    importances: dict,
    models_dir: Path,
    data_dir: Path,
) -> dict[str, Path]:
    """
    Save all training artifacts to disk.

    Artifacts:
      - Model:              rf_lst_predictor_{version}.joblib
      - Training report:    training_report_{version}.json
      - Train split:        train_split.csv
      - Test split:         test_split.csv

    Returns:
        Dict mapping artifact name to saved path.
    """
    paths = {}

    # ── Serialize model ──
    model_path = models_dir / f"rf_lst_predictor_{MODEL_VERSION}.joblib"
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path, compress=3)
    model_size_mb = model_path.stat().st_size / (1024 * 1024)
    logger.info(f"\n  Model saved: {model_path} ({model_size_mb:.1f} MB)")
    paths["model"] = model_path

    # ── Save train/test splits ──
    data_dir.mkdir(parents=True, exist_ok=True)

    train_path = data_dir / "train_split.csv"
    train_df.to_csv(train_path, index=False, float_format="%.6f")
    logger.info(f"  Train split saved: {train_path} ({len(train_df)} rows)")
    paths["train_split"] = train_path

    test_path = data_dir / "test_split.csv"
    test_df.to_csv(test_path, index=False, float_format="%.6f")
    logger.info(f"  Test split saved: {test_path} ({len(test_df)} rows)")
    paths["test_split"] = test_path

    # ── Save training report ──
    report = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "total_samples": len(train_df) + len(test_df),
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "test_size": TEST_SIZE,
            "split_random_state": SPLIT_RANDOM_STATE,
        },
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN_ALIAS,
        "hyperparameters": RF_PARAMS,
        "metrics": metrics,
        "feature_importances": importances,
        "pipeline_steps": [
            {"step": "SimpleImputer", "strategy": "median"},
            {"step": "RandomForestRegressor", **RF_PARAMS},
        ],
    }

    report_path = models_dir / f"training_report_{MODEL_VERSION}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"  Training report saved: {report_path}")
    paths["report"] = report_path

    return paths


# ══════════════════════════════════════════════════════════════
# CLI Entry Point
# ══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Train the ThermaCity Random Forest LST Predictor. "
            "Learns land-cover → temperature relationships for scenario simulation."
        ),
    )
    parser.add_argument(
        "--input", type=Path,
        default=Path(__file__).parent.parent / "data" / "training_set.csv",
        help="Path to merged training CSV (default: ../data/training_set.csv)",
    )
    parser.add_argument(
        "--models-dir", type=Path,
        default=Path(__file__).parent.parent / "models",
        help="Directory for model artifacts (default: ../models/)",
    )
    parser.add_argument(
        "--data-dir", type=Path,
        default=Path(__file__).parent.parent / "data",
        help="Directory for train/test splits (default: ../data/)",
    )
    args = parser.parse_args()

    # ── Validate input ──
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        logger.error(
            "Run gee/scripts/08_merge_features.py first to create the training set."
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("ThermaCity — Random Forest LST Predictor Training")
    logger.info("=" * 60)
    logger.info(f"  Model version:  {MODEL_VERSION}")
    logger.info(f"  Input:          {args.input.resolve()}")
    logger.info(f"  Features:       {FEATURE_COLUMNS}")
    logger.info(f"  Target:         {TARGET_COLUMN_ALIAS}")
    logger.info(f"  RF estimators:  {RF_PARAMS['n_estimators']}")
    logger.info(f"  RF max_depth:   {RF_PARAMS['max_depth']}")
    logger.info(f"  Test size:      {TEST_SIZE}")

    # ── Step 1: Load & validate ──
    df = load_and_validate_data(args.input)

    # ── Step 2: Train ──
    pipeline, train_df, test_df, metrics = train_model(df)

    # ── Step 3: Feature importances ──
    importance_path = args.models_dir / f"feature_importance_{MODEL_VERSION}.json"
    importances = extract_feature_importances(pipeline, importance_path)

    # ── Step 4: Save everything ──
    paths = save_artifacts(
        pipeline, train_df, test_df, metrics, importances,
        args.models_dir, args.data_dir,
    )

    # ── Final Summary ──
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING COMPLETE — SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Model:               {paths['model']}")
    logger.info(f"  Test R²:             {metrics['test_r2']:.4f}")
    logger.info(f"  Test RMSE:           {metrics['test_rmse']:.4f} °C")
    logger.info(f"  Test MAE:            {metrics['test_mae']:.4f} °C")
    logger.info(f"  Top feature:         {list(importances.keys())[0]}")
    logger.info(f"  Training time:       {metrics['training_time_seconds']:.1f}s")
    logger.info("=" * 60)
    logger.info(
        "\nNext step: run evaluate_model.py for detailed test-set analysis, "
        "or proceed to Phase 2 (backend integration)."
    )


if __name__ == "__main__":
    main()
