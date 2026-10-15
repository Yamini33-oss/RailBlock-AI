"""
===============================================================================
Unit Tests: Data Loader and Schema Adapter (data_loader.py)
===============================================================================
Tests loading of railway datasets, missing-file handling, and the
team schema adapter layer.
"""

from pathlib import Path
import pytest
import pandas as pd

from data_loader import DataLoader


class TestDataLoader:
    """Tests for DataLoader methods."""

    def test_load_all_datasets(self):
        loader = DataLoader(auto_generate=True)
        datasets = loader.load_all(validate=True)

        assert "delays" in datasets
        assert "schedules" in datasets
        assert "traffic" in datasets
        assert "maintenance" in datasets

        assert len(datasets["delays"]) > 100
        assert len(datasets["schedules"]) >= 10
        assert len(datasets["traffic"]) > 50
        assert len(datasets["maintenance"]) >= 5

    def test_missing_file_without_autogen_raises(self, tmp_path):
        fake_path = tmp_path / "non_existent_file.csv"
        loader = DataLoader(auto_generate=False)
        with pytest.raises(FileNotFoundError):
            loader.load_delays(file_path=fake_path)

    def test_adapt_member1_schema(self):
        external_df = pd.DataFrame(
            [
                {
                    "train_no": "12002",
                    "section_id": "SEC_NDLS_CNB",
                    "delay_mins": 12.5,
                    "date": "2026-10-01",
                }
            ]
        )

        adapted = DataLoader.adapt_schema(external_df, dataset_type="delays")
        assert "train_number" in adapted.columns
        assert "track_section" in adapted.columns
        assert "historical_delay_minutes" in adapted.columns
        assert "service_date" in adapted.columns

    def test_adapt_custom_mapping(self):
        custom_df = pd.DataFrame([{"my_special_train": "12951", "custom_delay": 5.0}])
        adapted = DataLoader.adapt_schema(
            custom_df,
            dataset_type="delays",
            custom_mapping={"my_special_train": "train_number", "custom_delay": "historical_delay_minutes"},
        )
        assert "train_number" in adapted.columns
        assert "historical_delay_minutes" in adapted.columns
