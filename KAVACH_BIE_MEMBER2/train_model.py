"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Model Training Pipeline and Model Selection
===============================================================================
Executes the supervised regression training workflow:
1. Loads validated historical delays and traffic density logs.
2. Constructs leak-free operational feature matrix.
3. Applies a chronological train/test split.
4. Trains and evaluates competing regression candidates:
   - DummyRegressor (Baseline)
   - Ridge Regressor (Linear)
   - RandomForestRegressor (Non-linear ensemble)
   - GradientBoostingRegressor (Boosting ensemble)
5. Selects the champion model based on lowest test MAE.
6. Saves the unified preprocessing + model pipeline and metadata via joblib.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

from config import (
    ALL_FEATURE_COLUMNS,
    CHRONOLOGICAL_SPLIT_RATIO,
    DATA_SOURCE,
    METADATA_FILE,
    MODEL_FILE,
    MODEL_VERSION,
    RANDOM_SEED,
    TARGET_COLUMN,
    TARGET_DESCRIPTION,
)
from data_loader import DataLoader
from feature_engineering import build_training_feature_matrix, create_preprocessing_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kavach_bie.trainer")


def split_chronologically(
    df: pd.DataFrame,
    split_ratio: float = CHRONOLOGICAL_SPLIT_RATIO,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split the dataset chronologically based on service_date to mirror
    real-world railway forecasting and prevent future lookahead leakage.
    """
    sorted_df = df.sort_values("service_date").reset_index(drop=True)
    unique_dates = sorted_df["service_date"].drop_duplicates().tolist()
    split_idx = int(len(unique_dates) * split_ratio)

    train_dates = set(unique_dates[:split_idx])
    test_dates = set(unique_dates[split_idx:])

    train_df = sorted_df[sorted_df["service_date"].isin(train_dates)].drop(columns=["service_date"])
    test_df = sorted_df[sorted_df["service_date"].isin(test_dates)].drop(columns=["service_date"])

    logger.info(
        "Chronological Split: %d training dates (%d rows), %d testing dates (%d rows)",
        len(train_dates),
        len(train_df),
        len(test_dates),
        len(test_df),
    )
    return train_df, test_df


def evaluate_candidate(
    pipeline: Pipeline,
    x_test: pd.DataFrame,
    y_test: pd.Series,
) -> Dict[str, float]:
    """Calculate MAE, RMSE, and R2 on the hold-out test set."""
    predictions = pipeline.predict(x_test)
    mae = float(mean_absolute_error(y_test, predictions))
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    r2 = float(r2_score(y_test, predictions))
    return {"mae": round(mae, 3), "rmse": round(rmse, 3), "r2": round(r2, 4)}


def run_training_pipeline() -> Tuple[Pipeline, Dict[str, Any]]:
    """Execute end-to-end training and candidate model comparison."""
    logger.info("Initializing DataLoader...")
    loader = DataLoader(auto_generate=True)
    delays_df = loader.load_delays()
    traffic_df = loader.load_traffic()

    if len(delays_df) < 50:
        raise ValueError(
            f"Insufficient historical delay samples ({len(delays_df)} rows). "
            "At least 50 samples are required to train the regression pipeline. "
            "Please run `python generate_data.py` to populate demonstration datasets."
        )

    logger.info("Building leak-free feature matrix from %d delay records...", len(delays_df))
    feature_matrix = build_training_feature_matrix(delays_df, traffic_df)

    train_df, test_df = split_chronologically(feature_matrix)

    x_train = train_df[ALL_FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]
    x_test = test_df[ALL_FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    # Candidate models to evaluate
    candidates = {
        "DummyBaseline": DummyRegressor(strategy="median"),
        "RidgeRegression": Ridge(alpha=1.0, random_state=RANDOM_SEED),
        "RandomForest": RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            min_samples_split=4,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.08,
            random_state=RANDOM_SEED,
        ),
    }

    results: Dict[str, Dict[str, float]] = {}
    trained_pipelines: Dict[str, Pipeline] = {}

    for name, model in candidates.items():
        logger.info("Training candidate model: %s...", name)
        preprocessor = create_preprocessing_pipeline()
        pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("regressor", model),
            ]
        )
        pipeline.fit(x_train, y_train)
        metrics = evaluate_candidate(pipeline, x_test, y_test)
        results[name] = metrics
        trained_pipelines[name] = pipeline
        logger.info(" -> %s | MAE: %.2f mins | RMSE: %.2f mins | R2: %.4f", name, metrics["mae"], metrics["rmse"], metrics["r2"])

    # Compute baseline comparison
    baseline_mae = results["DummyBaseline"]["mae"]
    for name in results:
        improvement = ((baseline_mae - results[name]["mae"]) / baseline_mae) * 100.0 if baseline_mae > 0 else 0.0
        results[name]["pct_improvement_over_baseline"] = round(improvement, 2)

    # Select champion model based on lowest test MAE among ML models
    ml_candidates = {k: v for k, v in results.items() if k != "DummyBaseline"}
    best_model_name = min(ml_candidates, key=lambda k: ml_candidates[k]["mae"])
    best_pipeline = trained_pipelines[best_model_name]
    best_metrics = results[best_model_name]

    logger.info(
        "[CHAMPION] Model '%s' selected with Test MAE: %.2f mins (%.1f%% improvement over baseline)",
        best_model_name,
        best_metrics["mae"],
        best_metrics["pct_improvement_over_baseline"],
    )

    # Assemble comprehensive model metadata
    metadata = {
        "model_version": MODEL_VERSION,
        "data_source": DATA_SOURCE,
        "prediction_target": TARGET_COLUMN,
        "target_description": TARGET_DESCRIPTION,
        "training_timestamp": datetime.now().isoformat(),
        "random_seed": RANDOM_SEED,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "best_model_name": best_model_name,
        "all_candidate_metrics": results,
        "champion_metrics": best_metrics,
        "feature_columns": ALL_FEATURE_COLUMNS,
        "synthetic_data_disclaimer": (
            "NOTICE: This model was trained on synthetic railway operation data. "
            "Metrics reflect synthetic environment properties and must not be "
            "interpreted as certified operational accuracy for real-world train networks."
        ),
    }

    # Save champion pipeline and metadata
    joblib.dump(best_pipeline, MODEL_FILE)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Saved trained pipeline to: %s", MODEL_FILE)
    logger.info("Saved model metadata to: %s", METADATA_FILE)

    return best_pipeline, metadata


if __name__ == "__main__":
    run_training_pipeline()
