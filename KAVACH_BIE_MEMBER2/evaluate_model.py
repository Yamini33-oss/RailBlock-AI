"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Comprehensive Model Evaluation and Reporting
===============================================================================
Performs in-depth evaluation of the trained delay prediction pipeline:
1. Reloads the saved model and checks inference integrity.
2. Evaluates performance against hold-out chronological test data.
3. Computes residual distribution statistics (median, percentiles, max error).
4. Extracts feature importances to highlight primary drivers of corridor delay.
5. Emits structured JSON and user-friendly Markdown reports into reports/.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config import (
    ALL_FEATURE_COLUMNS,
    EVALUATION_REPORT_JSON,
    EVALUATION_REPORT_MD,
    METADATA_FILE,
    MODEL_FILE,
    TARGET_COLUMN,
)
from data_loader import DataLoader
from feature_engineering import build_training_feature_matrix
from train_model import split_chronologically

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kavach_bie.evaluator")


def extract_feature_importances(pipeline: Any) -> List[Dict[str, Any]]:
    """Extract and rank feature importances or linear coefficients."""
    importances_list = []
    regressor = pipeline.named_steps.get("regressor")
    preprocessor = pipeline.named_steps.get("preprocessor")

    try:
        feature_names = preprocessor.get_feature_names_out()
    except Exception:
        feature_names = []

    if hasattr(regressor, "feature_importances_"):
        raw_vals = regressor.feature_importances_
        for name, val in zip(feature_names, raw_vals):
            clean_name = name.split("__")[-1]
            importances_list.append({"feature": clean_name, "importance": round(float(val), 4)})
        importances_list.sort(key=lambda x: x["importance"], reverse=True)

    elif hasattr(regressor, "coef_"):
        raw_vals = np.abs(regressor.coef_)
        total = np.sum(raw_vals) if np.sum(raw_vals) > 0 else 1.0
        normalized_vals = raw_vals / total
        for name, norm_val in zip(feature_names, normalized_vals):
            clean_name = name.split("__")[-1]
            importances_list.append({"feature": clean_name, "importance": round(float(norm_val), 4)})
        importances_list.sort(key=lambda x: x["importance"], reverse=True)

    return importances_list[:10]  # Return top 10



def compute_sliced_error_analysis(
    test_df: pd.DataFrame,
    y_test: pd.Series,
    y_pred: np.ndarray,
) -> Dict[str, Any]:
    """Compute MAE and RMSE breakdowns sliced by traffic level, section, and time period."""
    eval_df = test_df.copy()
    eval_df["y_true"] = y_test.values
    eval_df["y_pred"] = y_pred
    eval_df["abs_error"] = np.abs(eval_df["y_true"] - eval_df["y_pred"])
    eval_df["sq_error"] = (eval_df["y_true"] - eval_df["y_pred"]) ** 2

    # 1. By Traffic Density Level
    def categorize_density(d):
        if d < 0.60:
            return "LOW (<0.60)"
        elif d <= 0.85:
            return "MEDIUM (0.60-0.85)"
        return "HIGH (>0.85)"

    eval_df["traffic_tier"] = eval_df["traffic_density"].apply(categorize_density)
    by_traffic = {}
    for tier, group in eval_df.groupby("traffic_tier"):
        by_traffic[tier] = {
            "samples": len(group),
            "mae": round(float(group["abs_error"].mean()), 2),
            "rmse": round(float(np.sqrt(group["sq_error"].mean())), 2),
        }

    # 2. By Track Section
    by_section = {}
    for sec, group in eval_df.groupby("track_section"):
        by_section[sec] = {
            "samples": len(group),
            "mae": round(float(group["abs_error"].mean()), 2),
            "rmse": round(float(np.sqrt(group["sq_error"].mean())), 2),
        }

    # 3. By Operational Time Period
    by_period = {}
    for period, group in eval_df.groupby("time_period"):
        by_period[period] = {
            "samples": len(group),
            "mae": round(float(group["abs_error"].mean()), 2),
            "rmse": round(float(np.sqrt(group["sq_error"].mean())), 2),
        }

    return {
        "by_traffic_density": by_traffic,
        "by_track_section": by_section,
        "by_time_period": by_period,
    }


def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    """Format evaluation results into a clean, human-readable Markdown document."""
    metrics = report_data["test_metrics"]
    baseline = report_data["baseline_comparison"]
    residuals = report_data["residual_distribution"]
    candidates = report_data["candidate_models_summary"]
    slices = report_data.get("sliced_error_analysis", {})

    md = f"""# KAVACH BIE — Member 2: Model Evaluation Report
**AI/ML Train Delay Prediction Module**

> **IMPORTANT DISCLAIMER**: This evaluation was executed using deterministic **synthetic railway operational data**. The metrics below demonstrate model architecture, preprocessing pipeline integrity, and relative comparative performance. They must **not** be presented as certified real-world Indian Railways accuracy.

---

## 1. Executive Summary
- **Champion Model**: `{report_data['champion_model']}`
- **Model Version**: `{report_data['model_version']}`
- **Evaluation Date**: `{report_data['timestamp']}`
- **Prediction Target**: `{report_data['target_column']}`
- **Test Sample Size**: `{report_data['test_sample_count']}` records (chronological split)

| Evaluation Metric | Model Score | Baseline Score (Median) | Improvement | Railway Operations Interpretation |
|:---|:---:|:---:|:---:|:---|
| **MAE (Mean Absolute Error)** | **{metrics['mae']:.2f} mins** | {baseline['baseline_mae']:.2f} mins | **+{baseline['mae_improvement_pct']:.1f}%** | On average, predictions deviate by {metrics['mae']:.1f} minutes from scheduled section delay. |
| **RMSE (Root Mean Squared Error)** | **{metrics['rmse']:.2f} mins** | {baseline['baseline_rmse']:.2f} mins | **+{baseline['rmse_improvement_pct']:.1f}%** | Penalizes large delay outliers (e.g. major cascading congestion). |
| **R² (Coefficient of Determination)** | **{metrics['r2']:.4f}** | 0.0000 | N/A | Proportional variance in historical delay explained by corridor features. |

---

## 2. Multi-Model Benchmark Comparison
All candidate models were trained on identical training splits and evaluated on the hold-out chronological test set.

| Model Candidate | Test MAE (mins) | Test RMSE (mins) | Test R² | Status |
|:---|:---:|:---:|:---:|:---:|
"""
    for cand_name, cand_m in candidates.items():
        is_champ = cand_name == report_data["champion_model"]
        badge = "🏆 **Selected Champion**" if is_champ else "Evaluated"
        md += f"| `{cand_name}` | {cand_m.get('mae', 0):.2f} | {cand_m.get('rmse', 0):.2f} | {cand_m.get('r2', 0):.4f} | {badge} |\n"

    md += f"""
---

## 3. Residual Error Distribution
Analyzing the spread of prediction errors ($y_{{actual}} - \\hat{{y}}_{{predicted}}$) ensures predictions do not suffer from systemic bias:

- **Mean Error (Bias)**: `{residuals['mean_error']:.2f}` minutes
- **Median Absolute Error**: `{residuals['median_abs_error']:.2f}` minutes
- **25th Percentile Error**: `{residuals['p25_error']:.2f}` minutes
- **75th Percentile Error**: `{residuals['p75_error']:.2f}` minutes
- **95th Percentile Error**: `{residuals['p95_abs_error']:.2f}` minutes (95% of test predictions are within this error bound)
- **Max Absolute Error**: `{residuals['max_abs_error']:.2f}` minutes

---

## 4. Sliced Error Analysis
To ensure reliable operation across varying operational contexts, model performance is evaluated across operational slices:

### A. Performance by Corridor Traffic Density
| Traffic Level | Test Samples | MAE (mins) | RMSE (mins) | Operational Note |
|:---|:---:|:---:|:---:|:---|
"""
    for tier, data in slices.get("by_traffic_density", {}).items():
        md += f"| `{tier}` | {data['samples']} | **{data['mae']:.2f}** | {data['rmse']:.2f} | Error profile under {'heavy congestion' if 'HIGH' in tier else 'standard operations'} |\n"

    md += """
### B. Performance by Track Section Corridor
| Track Section | Test Samples | MAE (mins) | RMSE (mins) |
|:---|:---:|:---:|:---:|
"""
    for sec, data in slices.get("by_track_section", {}).items():
        md += f"| `{sec}` | {data['samples']} | **{data['mae']:.2f}** | {data['rmse']:.2f} |\n"

    md += """
### C. Performance by Operational Time Period
| Time Period | Test Samples | MAE (mins) | RMSE (mins) |
|:---|:---:|:---:|:---:|
"""
    for period, data in slices.get("by_time_period", {}).items():
        md += f"| `{period}` | {data['samples']} | **{data['mae']:.2f}** | {data['rmse']:.2f} |\n"

    md += f"""
---

## 5. Top Feature Influences
Relative importance of primary corridor and operational variables:

| Feature Name | Relative Importance Score | Operational Significance |
|:---|:---:|:---|
"""
    for feat in report_data.get("top_features", []):
        md += f"| `{feat['feature']}` | {feat['importance']:.4f} | Statistical correlation with section delay dynamics |\n"

    md += """
---

## 6. Metric Definitions for Railway Operations
1. **MAE (Mean Absolute Error)**: Average absolute magnitude of error. Useful for maintenance planners to gauge typical expected margin of error on timetables.
2. **RMSE (Root Mean Squared Error)**: Emphasizes larger errors heavily through squaring. Crucial for detecting whether severe delays are significantly underestimated.
3. **R² Score**: Quantifies the percentage of variation in corridor delay accounted for by schedule times, density, and corridor history.
"""
    return md



def run_evaluation() -> Dict[str, Any]:
    """Execute model evaluation and write JSON and Markdown reports."""
    if not MODEL_FILE.exists() or not METADATA_FILE.exists():
        logger.warning("Trained model or metadata not found. Triggering training first...")
        from train_model import run_training_pipeline
        run_training_pipeline()

    logger.info("Loading model pipeline from: %s", MODEL_FILE)
    pipeline = joblib.load(MODEL_FILE)

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    loader = DataLoader(auto_generate=True)
    delays_df = loader.load_delays()
    traffic_df = loader.load_traffic()

    feature_matrix = build_training_feature_matrix(delays_df, traffic_df)
    _, test_df = split_chronologically(feature_matrix)

    x_test = test_df[ALL_FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    # Model predictions
    y_pred = pipeline.predict(x_test)

    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    # Baseline calculations
    median_baseline = float(y_test.median())
    y_baseline = np.full_like(y_test, fill_value=median_baseline)
    base_mae = float(mean_absolute_error(y_test, y_baseline))
    base_rmse = float(np.sqrt(mean_squared_error(y_test, y_baseline)))

    mae_imp = ((base_mae - mae) / base_mae) * 100.0 if base_mae > 0 else 0.0
    rmse_imp = ((base_rmse - rmse) / base_rmse) * 100.0 if base_rmse > 0 else 0.0

    # Residuals
    residuals = y_test - y_pred
    abs_residuals = np.abs(residuals)

    top_features = extract_feature_importances(pipeline)
    sliced_analysis = compute_sliced_error_analysis(test_df, y_test, y_pred)

    report_payload: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "model_version": metadata.get("model_version", "1.1.0"),
        "champion_model": metadata.get("best_model_name", "RandomForest"),
        "target_column": TARGET_COLUMN,
        "test_sample_count": len(test_df),
        "test_metrics": {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 4),
        },
        "baseline_comparison": {
            "baseline_mae": round(base_mae, 3),
            "baseline_rmse": round(base_rmse, 3),
            "mae_improvement_pct": round(mae_imp, 2),
            "rmse_improvement_pct": round(rmse_imp, 2),
        },
        "residual_distribution": {
            "mean_error": round(float(np.mean(residuals)), 3),
            "median_abs_error": round(float(np.median(abs_residuals)), 3),
            "p25_error": round(float(np.percentile(residuals, 25)), 3),
            "p75_error": round(float(np.percentile(residuals, 75)), 3),
            "p95_abs_error": round(float(np.percentile(abs_residuals, 95)), 3),
            "max_abs_error": round(float(np.max(abs_residuals)), 3),
        },
        "candidate_models_summary": metadata.get("all_candidate_metrics", {}),
        "top_features": top_features,
        "sliced_error_analysis": sliced_analysis,
        "synthetic_disclaimer": metadata.get("synthetic_data_disclaimer"),
    }


    # Save JSON report
    with open(EVALUATION_REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)
    logger.info("Saved JSON evaluation report: %s", EVALUATION_REPORT_JSON)

    # Save Markdown report
    md_content = generate_markdown_report(report_payload)
    with open(EVALUATION_REPORT_MD, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("Saved Markdown evaluation report: %s", EVALUATION_REPORT_MD)

    return report_payload


if __name__ == "__main__":
    run_evaluation()
