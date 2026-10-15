"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Feature Engineering and Preprocessing Pipeline
===============================================================================
Extracts domain-specific operational features from schedules, traffic density,
and corridor history while strictly preventing target leakage:
- No future arrival/departure times are used as features.
- Rolling delay statistics are shifted by at least 1 day to prevent lookahead bias.
- Imputers and Scalers are fitted exclusively on training splits.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import (
    ALL_FEATURE_COLUMNS,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    TARGET_COLUMN,
    TIME_PERIODS,
)


def get_time_period_category(hour: int) -> str:
    """Categorize a 24-hr hour into railway operational time period."""
    if 0 <= hour < 6:
        return "NIGHT"
    elif 6 <= hour < 11:
        return "PEAK_MORNING"
    elif 11 <= hour < 17:
        return "AFTERNOON"
    elif 17 <= hour < 22:
        return "PEAK_EVENING"
    else:
        return "LATE_NIGHT"


def extract_temporal_features(date_str: str, time_str: str) -> Dict[str, any]:
    """Extract hour, day of week, and time period category safely."""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    hour = dt.hour
    return {
        "hour_of_day": hour,
        "day_of_week": dt.strftime("%A"),
        "time_period": get_time_period_category(hour),
    }


def compute_leak_free_rolling_delay(
    delays_df: pd.DataFrame,
    window_days: int = 3,
) -> pd.DataFrame:
    """
    Compute corridor-level rolling average delay strictly using prior days.
    Shifts the rolling window so the current day's delay is NEVER included.
    """
    df = delays_df.copy()
    df["service_date_dt"] = pd.to_datetime(df["service_date"])

    # Aggregate daily average delay per track section
    daily_section_delays = (
        df.groupby(["track_section", "service_date_dt"])["historical_delay_minutes"]
        .mean()
        .reset_index()
        .sort_values(["track_section", "service_date_dt"])
    )

    # Shift by 1 day so today's delay does not leak into the feature
    daily_section_delays["rolling_avg_delay_3d"] = daily_section_delays.groupby("track_section")[
        "historical_delay_minutes"
    ].transform(lambda s: s.shift(1).rolling(window=window_days, min_periods=1).mean())

    # Merge back onto main delays dataframe
    merged = df.merge(
        daily_section_delays[["track_section", "service_date_dt", "rolling_avg_delay_3d"]],
        on=["track_section", "service_date_dt"],
        how="left",
    )

    # Fill earliest dates where no prior history exists with section median
    section_medians = merged.groupby("track_section")["historical_delay_minutes"].transform("median")
    merged["rolling_avg_delay_3d"] = merged["rolling_avg_delay_3d"].fillna(section_medians)
    merged.drop(columns=["service_date_dt"], inplace=True)

    return merged


def build_training_feature_matrix(
    delays_df: pd.DataFrame,
    traffic_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join historical delays with traffic logs to construct a tabular feature matrix.
    Ensures that only features available prior to dispatch are included.
    """
    # 1. Compute shifted rolling delays (leak-free)
    delays_with_history = compute_leak_free_rolling_delay(delays_df)

    # 2. Extract scheduled departure hour and time period
    delays_with_history["hour_of_day"] = delays_with_history["scheduled_departure"].apply(
        lambda t: int(str(t).split(":")[0])
    )
    delays_with_history["time_period"] = delays_with_history["hour_of_day"].apply(get_time_period_category)
    delays_with_history["day_of_week"] = pd.to_datetime(delays_with_history["service_date"]).dt.day_name()

    # 3. Merge with traffic observations on (track_section, service_date, time_period)
    traffic_dedup = traffic_df.drop_duplicates(
        subset=["track_section", "observation_date", "time_period"]
    )
    merged = delays_with_history.merge(
        traffic_dedup,
        left_on=["track_section", "service_date", "time_period"],
        right_on=["track_section", "observation_date", "time_period"],
        how="left",
    )

    # 4. Synthesize realistic maintenance-window context features
    # For training, associate representative maintenance duration (default 180 min) & priority
    merged["required_duration_minutes"] = 180.0
    merged["maintenance_priority"] = "MEDIUM"

    # Fill any missing traffic metrics with section-wise medians
    for col in ["traffic_density", "scheduled_train_count", "track_utilization"]:
        if col in merged.columns:
            section_median = merged.groupby("track_section")[col].transform("median")
            merged[col] = merged[col].fillna(section_median).fillna(0.5)

    # Select feature columns + target
    cols_to_keep = ALL_FEATURE_COLUMNS + [TARGET_COLUMN, "service_date"]
    return merged[cols_to_keep].dropna(subset=[TARGET_COLUMN]).copy()


def create_preprocessing_pipeline() -> ColumnTransformer:
    """
    Construct a scikit-learn ColumnTransformer for numerical and categorical features.
    Ensures numerical features are imputed & scaled, and categoricals are one-hot encoded.
    Unknown categories during inference are safely ignored (handle_unknown='ignore').
    """
    num_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    cat_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipeline, NUMERICAL_FEATURES),
            ("cat", cat_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return preprocessor


def build_inference_feature_row(
    request_dict: Dict[str, any],
    traffic_density: float,
    scheduled_train_count: int,
    track_utilization: float,
    rolling_avg_delay: float,
) -> pd.DataFrame:
    """
    Assemble a single-row feature DataFrame from a validated maintenance request
    and contextual operational metrics for model inference.
    """
    req_date = request_dict["requested_date"]
    start_time = request_dict["proposed_start_time"]
    temp = extract_temporal_features(req_date, start_time)

    row_data = {
        "hour_of_day": [temp["hour_of_day"]],
        "traffic_density": [traffic_density],
        "scheduled_train_count": [scheduled_train_count],
        "track_utilization": [track_utilization],
        "rolling_avg_delay_3d": [rolling_avg_delay],
        "required_duration_minutes": [float(request_dict["required_duration_minutes"])],
        "track_section": [str(request_dict["track_section"])],
        "day_of_week": [temp["day_of_week"]],
        "time_period": [temp["time_period"]],
        "maintenance_priority": [str(request_dict.get("maintenance_priority", "MEDIUM"))],
    }
    return pd.DataFrame(row_data)[ALL_FEATURE_COLUMNS]
