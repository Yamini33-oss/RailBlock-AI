"""
===============================================================================
Unit Tests: Feature Engineering & Preprocessing (feature_engineering.py)
===============================================================================
Tests temporal extraction, leak-free rolling calculations, and preprocessing
pipeline transformations.
"""

import pandas as pd
import numpy as np

from config import ALL_FEATURE_COLUMNS, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from feature_engineering import (
    build_inference_feature_row,
    build_training_feature_matrix,
    compute_leak_free_rolling_delay,
    create_preprocessing_pipeline,
    extract_temporal_features,
    get_time_period_category,
)


class TestTemporalExtraction:
    """Tests for temporal helper functions."""

    def test_get_time_period_category(self):
        assert get_time_period_category(2) == "NIGHT"
        assert get_time_period_category(8) == "PEAK_MORNING"
        assert get_time_period_category(14) == "AFTERNOON"
        assert get_time_period_category(19) == "PEAK_EVENING"
        assert get_time_period_category(23) == "LATE_NIGHT"

    def test_extract_temporal_features(self):
        feat = extract_temporal_features("2026-10-15", "08:30")
        assert feat["hour_of_day"] == 8
        assert feat["time_period"] == "PEAK_MORNING"
        assert feat["day_of_week"] == "Thursday"


class TestLeakFreeRollingDelay:
    """Verifies that rolling delay strictly uses prior days (no lookahead leakage)."""

    def test_no_same_day_leakage(self):
        delays_data = pd.DataFrame(
            [
                {"track_section": "SEC_TEST", "service_date": "2026-09-01", "historical_delay_minutes": 10.0},
                {"track_section": "SEC_TEST", "service_date": "2026-09-02", "historical_delay_minutes": 20.0},
                {"track_section": "SEC_TEST", "service_date": "2026-09-03", "historical_delay_minutes": 30.0},
            ]
        )
        res = compute_leak_free_rolling_delay(delays_data, window_days=2)

        # On 2026-09-02, rolling average should only reflect Day 1 (10.0), NOT Day 2 (20.0)
        day2_row = res[res["service_date"] == "2026-09-02"].iloc[0]
        assert day2_row["rolling_avg_delay_3d"] == 10.0

        # On 2026-09-03, rolling average should reflect mean of Day 1 & Day 2 ((10+20)/2 = 15.0), NOT Day 3 (30.0)
        day3_row = res[res["service_date"] == "2026-09-03"].iloc[0]
        assert day3_row["rolling_avg_delay_3d"] == 15.0


class TestPreprocessingPipeline:
    """Tests for scikit-learn ColumnTransformer."""

    def test_pipeline_transforms_cleanly(self):
        preprocessor = create_preprocessing_pipeline()

        sample_df = pd.DataFrame(
            [
                {
                    "hour_of_day": 8,
                    "traffic_density": 0.75,
                    "scheduled_train_count": 12,
                    "track_utilization": 0.85,
                    "rolling_avg_delay_3d": 14.0,
                    "required_duration_minutes": 180.0,
                    "track_section": "SEC_NDLS_CNB",
                    "day_of_week": "Monday",
                    "time_period": "PEAK_MORNING",
                    "maintenance_priority": "HIGH",
                }
            ]
        )

        transformed = preprocessor.fit_transform(sample_df)
        assert isinstance(transformed, np.ndarray)
        assert transformed.shape[0] == 1
        assert not np.isnan(transformed).any()

    def test_handles_unseen_categories_gracefully(self):
        preprocessor = create_preprocessing_pipeline()

        train_df = pd.DataFrame(
            [
                {
                    "hour_of_day": 10,
                    "traffic_density": 0.6,
                    "scheduled_train_count": 8,
                    "track_utilization": 0.7,
                    "rolling_avg_delay_3d": 10.0,
                    "required_duration_minutes": 120.0,
                    "track_section": "SEC_NDLS_CNB",
                    "day_of_week": "Tuesday",
                    "time_period": "PEAK_MORNING",
                    "maintenance_priority": "MEDIUM",
                }
            ]
        )
        preprocessor.fit(train_df)

        # Unseen corridor section during inference
        unseen_df = train_df.copy()
        unseen_df.loc[0, "track_section"] = "SEC_BRAND_NEW_CORRIDOR"
        transformed_unseen = preprocessor.transform(unseen_df)
        assert transformed_unseen.shape[0] == 1
        assert not np.isnan(transformed_unseen).any()
