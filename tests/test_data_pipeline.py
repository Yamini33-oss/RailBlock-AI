"""Automated tests for the real railway data pipeline and data quality assertions."""

from pathlib import Path
import pandas as pd
import pytest

from app.config import settings
from scripts.discover_datasets import discover_datasets
from scripts.validate_datasets import validate_all_datasets


def test_discover_datasets_generates_valid_catalog():
    catalog = discover_datasets()
    assert "catalog_version" in catalog
    assert catalog["total_sources_discovered"] >= 4
    dataset_ids = [d["dataset_id"] for d in catalog["datasets"]]
    assert "ir_stations_master" in dataset_ids
    assert "ir_trains_master" in dataset_ids
    assert "ir_schedules_master" in dataset_ids


def test_processed_stations_dataset_exists_and_valid():
    p = settings.DATA_PROCESSED_DIR / "stations_processed.csv"
    assert p.exists(), "stations_processed.csv must exist"
    df = pd.read_csv(p)
    assert len(df) > 8000, f"Expected >8000 stations, got {len(df)}"
    assert "station_code" in df.columns
    assert "station_name" in df.columns
    assert "state" in df.columns
    assert "zone" in df.columns
    # Check zero duplicates in station_code
    assert df["station_code"].duplicated().sum() == 0


def test_processed_trains_dataset_exists_and_valid():
    p = settings.DATA_PROCESSED_DIR / "trains_processed.csv"
    assert p.exists(), "trains_processed.csv must exist"
    df = pd.read_csv(p)
    assert len(df) > 5000, f"Expected >5000 trains, got {len(df)}"
    assert "train_number" in df.columns
    assert "train_name" in df.columns
    assert "train_type" in df.columns
    # Check zero duplicates in train_number
    assert df["train_number"].duplicated().sum() == 0


def test_processed_schedules_dataset_exists_and_large():
    p = settings.DATA_PROCESSED_DIR / "schedules_processed.csv"
    assert p.exists(), "schedules_processed.csv must exist"
    df = pd.read_csv(p)
    # Check this is a real large dataset (>100,000 rows)
    assert len(df) > 100000, f"Expected >100,000 schedules, got {len(df)}"
    assert "train_number" in df.columns
    assert "station_code" in df.columns
    assert "arrival_time" in df.columns
    assert "departure_time" in df.columns


def test_processed_traffic_density_exists():
    p = settings.DATA_PROCESSED_DIR / "section_traffic_density_processed.csv"
    assert p.exists(), "section_traffic_density_processed.csv must exist"
    df = pd.read_csv(p)
    assert len(df) > 0
    assert "traffic_density_score" in df.columns
    assert ((df["traffic_density_score"] >= 0.0) & (df["traffic_density_score"] <= 1.0)).all()


def test_validation_suite_passes():
    report = validate_all_datasets()
    assert report["overall_status"] == "PASSED"
    assert report["datasets"]["stations"]["passed"] is True
    assert report["datasets"]["trains"]["passed"] is True
    assert report["datasets"]["schedules"]["passed"] is True
    assert report["datasets"]["traffic_density"]["passed"] is True
