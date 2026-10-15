"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Configuration and Domain Constants
===============================================================================
This module defines filesystem paths, model parameters, disruption score
weights, risk category thresholds, and corridor metadata for the delay
prediction engine. All paths are resolved dynamically using pathlib to ensure
seamless cross-platform operation (Windows, Linux, macOS).
"""

from pathlib import Path
from typing import Dict, List, Tuple

# -----------------------------------------------------------------------------
# Base Directories and Paths
# -----------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"
MODELS_DIR: Path = BASE_DIR / "models"
REPORTS_DIR: Path = BASE_DIR / "reports"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Data File Paths
DELAYS_DATA_FILE: Path = DATA_DIR / "sample_train_delays.csv"
SCHEDULES_DATA_FILE: Path = DATA_DIR / "sample_train_schedules.csv"
TRAFFIC_DATA_FILE: Path = DATA_DIR / "sample_traffic_density.csv"
MAINTENANCE_DATA_FILE: Path = DATA_DIR / "sample_maintenance_windows.csv"

# Model and Artifact File Paths
MODEL_FILE: Path = MODELS_DIR / "delay_predictor_pipeline.joblib"
METADATA_FILE: Path = MODELS_DIR / "model_metadata.json"
EVALUATION_REPORT_JSON: Path = REPORTS_DIR / "evaluation_report.json"
EVALUATION_REPORT_MD: Path = REPORTS_DIR / "evaluation_report.md"
DATA_QUALITY_REPORT_JSON: Path = REPORTS_DIR / "data_quality_report.json"

# -----------------------------------------------------------------------------
# Machine Learning Target and Feature Configuration
# -----------------------------------------------------------------------------
MODEL_VERSION: str = "1.1.0"
DATA_SOURCE: str = "synthetic_railway_demo"

TARGET_COLUMN: str = "historical_delay_minutes"
PREDICTION_TARGET_NAME: str = "baseline_arrival_delay_minutes"
DISRUPTION_SCORE_NAME: str = "maintenance_exposure_score"

TARGET_DESCRIPTION: str = (
    "Expected average train delay in minutes for services operating across the "
    "specified track section during or near the maintenance window, estimated "
    "from historical corridor delay dynamics, traffic density, and schedule density."
)

RANDOM_SEED: int = 42
CHRONOLOGICAL_SPLIT_RATIO: float = 0.80

NUMERICAL_FEATURES: List[str] = [
    "hour_of_day",
    "traffic_density",
    "scheduled_train_count",
    "track_utilization",
    "rolling_avg_delay_3d",
    "required_duration_minutes",
]

CATEGORICAL_FEATURES: List[str] = [
    "track_section",
    "day_of_week",
    "time_period",
    "maintenance_priority",
]

ALL_FEATURE_COLUMNS: List[str] = NUMERICAL_FEATURES + CATEGORICAL_FEATURES

# -----------------------------------------------------------------------------
# Known Railway Track Sections (Corridor Registry)
# -----------------------------------------------------------------------------
KNOWN_TRACK_SECTIONS: Dict[str, Dict[str, str]] = {
    "SEC_NDLS_CNB": {
        "name": "New Delhi - Kanpur Central",
        "zone": "North Central Railway (NCR)",
        "type": "High Density Trunk",
        "typical_daily_trains": "120+",
    },
    "SEC_CNB_PRYJ": {
        "name": "Kanpur Central - Prayagraj",
        "zone": "North Central Railway (NCR)",
        "type": "Heavy Freight & Passenger",
        "typical_daily_trains": "100+",
    },
    "SEC_BCT_ST": {
        "name": "Mumbai Central - Surat",
        "zone": "Western Railway (WR)",
        "type": "High Frequency Suburban & Express",
        "typical_daily_trains": "110+",
    },
    "SEC_HWH_ASN": {
        "name": "Howrah - Asansol",
        "zone": "Eastern Railway (ER)",
        "type": "Mineral Freight & Passenger Corridor",
        "typical_daily_trains": "90+",
    },
    "SEC_SBC_MAS": {
        "name": "KSR Bengaluru - Chennai Central",
        "zone": "Southern Railway (SR)",
        "type": "Intercity & Express Corridor",
        "typical_daily_trains": "75+",
    },
    "SEC_GKP_BST": {
        "name": "Gorakhpur - Basti",
        "zone": "North Eastern Railway (NER)",
        "type": "Regional Semi-Trunk",
        "typical_daily_trains": "50+",
    },
}

# -----------------------------------------------------------------------------
# Operational Constants & Disruption Score Formula
# -----------------------------------------------------------------------------
DEFAULT_SAFETY_BUFFER_MINUTES: int = 30
MAX_WINDOW_DURATION_HOURS: float = 24.0

# Disruption Score Weights:
# Disruption Score = [ (Delay * W_delay) + (Density * 20 * W_density) +
#                      (AffectedTrains * 10 * W_trains) +
#                      ((Duration/60) * 5 * W_duration) ] * PriorityMultiplier
WEIGHT_DELAY: float = 0.35
WEIGHT_DENSITY: float = 0.25
WEIGHT_AFFECTED_TRAINS: float = 0.25
WEIGHT_DURATION: float = 0.15

PRIORITY_MULTIPLIERS: Dict[str, float] = {
    "CRITICAL": 1.25,
    "HIGH": 1.15,
    "MEDIUM": 1.00,
    "LOW": 0.85,
}

# Risk Category Classification Thresholds (Score-based)
RISK_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    "LOW": (0.0, 25.0),
    "MEDIUM": (25.0, 50.0),
    "HIGH": (50.0, 75.0),
    "CRITICAL": (75.0, float("inf")),
}

# Time Period Bins (24-hour clock)
TIME_PERIODS: Dict[str, Tuple[int, int]] = {
    "NIGHT": (0, 6),
    "PEAK_MORNING": (6, 11),
    "AFTERNOON": (11, 17),
    "PEAK_EVENING": (17, 22),
    "LATE_NIGHT": (22, 24),
}

# Out-of-Distribution (OOD) Operational Bounds
OOD_MAX_TRAFFIC_DENSITY: float = 1.25
OOD_MAX_EXISTING_DELAY: float = 180.0  # > 3 hours rolling delay indicates extreme event
OOD_MAX_DURATION_MINUTES: float = 720.0  # > 12 hours block possession is exceptional

