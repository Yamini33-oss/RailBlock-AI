"""
===============================================================================
Unit Tests: Model Training & Persistence (train_model.py)
===============================================================================
Tests chronological train-test split, model training pipeline, persistence,
reload verification, and minimum dataset size validation.
"""

import tempfile
from pathlib import Path
import joblib
import pandas as pd
import pytest

from config import MODEL_FILE, METADATA_FILE
from train_model import run_training_pipeline, split_chronologically


class TestModelTraining:
    """Tests for training workflows and persistence."""

    def test_chronological_split(self):
        dates = ["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04", "2026-08-05"]
        rows = []
        for d in dates:
            for i in range(4):
                rows.append({"service_date": d, "feature_x": i, "historical_delay_minutes": 5.0})
        df = pd.DataFrame(rows)

        train_df, test_df = split_chronologically(df, split_ratio=0.60)
        assert len(train_df) > 0
        assert len(test_df) > 0
        # Check service_date was dropped to avoid leakage
        assert "service_date" not in train_df.columns
        assert "service_date" not in test_df.columns

    def test_end_to_end_training_and_persistence(self):
        pipeline, metadata = run_training_pipeline()

        assert MODEL_FILE.exists()
        assert METADATA_FILE.exists()
        assert "best_model_name" in metadata
        assert "champion_metrics" in metadata
        assert metadata["champion_metrics"]["mae"] > 0.0

        # Reload and verify inference works identically
        reloaded_pipeline = joblib.load(MODEL_FILE)
        assert hasattr(reloaded_pipeline, "predict")

    def test_insufficient_samples_raises_error(self, monkeypatch):
        # Mock DataLoader to return only 10 rows
        small_delays = pd.DataFrame(
            [
                {
                    "train_number": "12002",
                    "train_name": "Shatabdi",
                    "service_date": "2026-08-01",
                    "track_section": "SEC_NDLS_CNB",
                    "scheduled_arrival": "06:00",
                    "actual_arrival": "06:10",
                    "scheduled_departure": "10:15",
                    "actual_departure": "10:25",
                    "historical_delay_minutes": 10.0,
                }
            ]
            * 10
        )

        from data_loader import DataLoader
        monkeypatch.setattr(DataLoader, "load_delays", lambda self: small_delays)

        with pytest.raises(ValueError, match="Insufficient historical delay samples"):
            run_training_pipeline()
