"""Dataset preprocessing pipeline for KAVACH BIE Member 3.

Processes large raw Indian Railways datasets into clean, normalized CSVs:
1. data/processed/stations_processed.csv (8,990+ stations)
2. data/processed/trains_processed.csv (5,208 train services)
3. data/processed/schedules_processed.csv (417,080 timetable stop records)
4. data/processed/track_sections_processed.csv (Key trunk track sections)
5. data/processed/section_traffic_density_processed.csv (Derived hourly traffic density)

Outputs comprehensive data quality metrics to data/metadata/preprocessing_metadata.json.
"""

import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
METADATA_DIR = BASE_DIR / "data" / "metadata"
PREPROCESSING_META_FILE = METADATA_DIR / "preprocessing_metadata.json"


def compute_column_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate missing values and unique counts per column."""
    stats = {}
    total_rows = len(df)
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        stats[col] = {
            "dtype": str(df[col].dtype),
            "null_count": null_count,
            "null_percentage": round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0,
            "unique_count": int(df[col].nunique()),
        }
    return stats


def preprocess_stations() -> Dict[str, Any]:
    """Preprocess stations_raw.json into stations_processed.csv."""
    raw_path = RAW_DIR / "stations_raw.json"
    out_path = PROCESSED_DIR / "stations_processed.csv"
    logger.info("Preprocessing stations from %s...", raw_path.name)

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [None, None]) if geom else [None, None]
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None

        records.append({
            "station_code": str(props.get("code", "")).strip().upper(),
            "station_name": str(props.get("name", "")).strip(),
            "state": str(props.get("state", "")).strip() or "UNKNOWN",
            "zone": str(props.get("zone", "")).strip() or "IR",
            "address": str(props.get("address", "")).strip(),
            "latitude": lat,
            "longitude": lon,
        })

    df = pd.DataFrame(records)
    initial_count = len(df)
    df.drop_duplicates(subset=["station_code"], inplace=True)
    df.sort_values(by="station_code", inplace=True)
    df.to_csv(out_path, index=False, encoding="utf-8")

    logger.info("Wrote %d stations to %s (initial: %d)", len(df), out_path.name, initial_count)
    return {
        "dataset": "stations_processed.csv",
        "rows": len(df),
        "columns": len(df.columns),
        "file_size_bytes": out_path.stat().st_size,
        "duplicates_removed": initial_count - len(df),
        "column_stats": compute_column_stats(df),
    }


def preprocess_trains() -> Dict[str, Any]:
    """Preprocess trains_raw.json into trains_processed.csv."""
    raw_path = RAW_DIR / "trains_raw.json"
    out_path = PROCESSED_DIR / "trains_processed.csv"
    logger.info("Preprocessing trains from %s...", raw_path.name)

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        records.append({
            "train_number": str(props.get("number", "")).strip().zfill(5),
            "train_name": str(props.get("name", "")).strip(),
            "train_type": str(props.get("type", "MAIL/EXPRESS")).strip().upper(),
            "zone": str(props.get("zone", "")).strip() or "IR",
            "from_station_code": str(props.get("from_station_code", "")).strip().upper(),
            "from_station_name": str(props.get("from_station_name", "")).strip(),
            "to_station_code": str(props.get("to_station_code", "")).strip().upper(),
            "to_station_name": str(props.get("to_station_name", "")).strip(),
            "departure_time": str(props.get("departure", "00:00:00")).strip(),
            "arrival_time": str(props.get("arrival", "00:00:00")).strip(),
            "duration_hours": int(props.get("duration_h", 0) or 0),
            "duration_minutes": int(props.get("duration_m", 0) or 0),
            "distance_km": float(props.get("distance", 0.0) or 0.0),
        })

    df = pd.DataFrame(records)
    initial_count = len(df)
    df.drop_duplicates(subset=["train_number"], inplace=True)
    df.sort_values(by="train_number", inplace=True)
    df.to_csv(out_path, index=False, encoding="utf-8")

    logger.info("Wrote %d trains to %s (initial: %d)", len(df), out_path.name, initial_count)
    return {
        "dataset": "trains_processed.csv",
        "rows": len(df),
        "columns": len(df.columns),
        "file_size_bytes": out_path.stat().st_size,
        "duplicates_removed": initial_count - len(df),
        "column_stats": compute_column_stats(df),
    }


def preprocess_schedules() -> Dict[str, Any]:
    """Preprocess schedules_raw.json into schedules_processed.csv."""
    raw_path = RAW_DIR / "schedules_raw.json"
    out_path = PROCESSED_DIR / "schedules_processed.csv"
    logger.info("Preprocessing schedules from %s (417,000+ records)...", raw_path.name)

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for item in data:
        arr = str(item.get("arrival", "")).strip()
        dep = str(item.get("departure", "")).strip()
        if arr == "None":
            arr = dep
        if dep == "None":
            dep = arr

        records.append({
            "stop_id": int(item.get("id", 0)),
            "train_number": str(item.get("train_number", "")).strip().zfill(5),
            "train_name": str(item.get("train_name", "")).strip(),
            "station_code": str(item.get("station_code", "")).strip().upper(),
            "station_name": str(item.get("station_name", "")).strip(),
            "day": int(item.get("day", 1) or 1),
            "arrival_time": arr,
            "departure_time": dep,
        })

    df = pd.DataFrame(records)
    initial_count = len(df)
    df.drop_duplicates(subset=["stop_id"], inplace=True)
    df.sort_values(by=["train_number", "day", "arrival_time"], inplace=True)
    df.to_csv(out_path, index=False, encoding="utf-8")

    logger.info("Wrote %d schedules to %s (initial: %d)", len(df), out_path.name, initial_count)
    return {
        "dataset": "schedules_processed.csv",
        "rows": len(df),
        "columns": len(df.columns),
        "file_size_bytes": out_path.stat().st_size,
        "duplicates_removed": initial_count - len(df),
        "column_stats": compute_column_stats(df),
    }


def generate_track_sections_and_density(schedules_df: pd.DataFrame) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Derive corridor track block sections and hourly traffic density from real schedules."""
    logger.info("Deriving trunk track sections and hourly traffic density...")
    sections_out_path = PROCESSED_DIR / "track_sections_processed.csv"
    density_out_path = PROCESSED_DIR / "section_traffic_density_processed.csv"

    # Define high-density railway trunk corridor sections
    trunk_sections = [
        {
            "track_section_id": "SEC-NDLS-MTJ",
            "section_name": "New Delhi - Mathura Jn",
            "from_station_code": "NDLS",
            "to_station_code": "MTJ",
            "zone": "NR/NCR",
            "distance_km": 141.0,
            "is_electrified": True,
            "tracks": 3,
            "max_speed_kmh": 130,
        },
        {
            "track_section_id": "SEC-MTJ-AGC",
            "section_name": "Mathura Jn - Agra Cantt",
            "from_station_code": "MTJ",
            "to_station_code": "AGC",
            "zone": "NCR",
            "distance_km": 54.0,
            "is_electrified": True,
            "tracks": 3,
            "max_speed_kmh": 130,
        },
        {
            "track_section_id": "SEC-AGC-GWL",
            "section_name": "Agra Cantt - Gwalior Jn",
            "from_station_code": "AGC",
            "to_station_code": "GWL",
            "zone": "NCR",
            "distance_km": 118.0,
            "is_electrified": True,
            "tracks": 2,
            "max_speed_kmh": 120,
        },
        {
            "track_section_id": "SEC-GWL-JHS",
            "section_name": "Gwalior Jn - VGLB Jhansi",
            "from_station_code": "GWL",
            "to_station_code": "JHS",
            "zone": "NCR",
            "distance_km": 97.0,
            "is_electrified": True,
            "tracks": 2,
            "max_speed_kmh": 120,
        },
        {
            "track_section_id": "SEC-JHS-BPL",
            "section_name": "VGLB Jhansi - Bhopal Jn",
            "from_station_code": "JHS",
            "to_station_code": "BPL",
            "zone": "NCR/WCR",
            "distance_km": 292.0,
            "is_electrified": True,
            "tracks": 2,
            "max_speed_kmh": 120,
        },
        {
            "track_section_id": "SEC-HWH-BWN",
            "section_name": "Howrah - Barddhaman Jn",
            "from_station_code": "HWH",
            "to_station_code": "BWN",
            "zone": "ER",
            "distance_km": 107.0,
            "is_electrified": True,
            "tracks": 4,
            "max_speed_kmh": 130,
        },
        {
            "track_section_id": "SEC-BWN-ASN",
            "section_name": "Barddhaman - Asansol Jn",
            "from_station_code": "BWN",
            "to_station_code": "ASN",
            "zone": "ER",
            "distance_km": 106.0,
            "is_electrified": True,
            "tracks": 3,
            "max_speed_kmh": 130,
        },
        {
            "track_section_id": "SEC-CSMT-KYN",
            "section_name": "Mumbai CSMT - Kalyan Jn",
            "from_station_code": "CSMT",
            "to_station_code": "KYN",
            "zone": "CR",
            "distance_km": 54.0,
            "is_electrified": True,
            "tracks": 4,
            "max_speed_kmh": 110,
        },
    ]

    sec_df = pd.DataFrame(trunk_sections)
    sec_df.to_csv(sections_out_path, index=False, encoding="utf-8")

    # Compute hourly traffic density for each trunk section
    # Count trains whose schedules include the station codes in each hour
    density_records = []
    st_codes_map = {
        s["track_section_id"]: {s["from_station_code"], s["to_station_code"]}
        for s in trunk_sections
    }

    # Extract departure hour from schedules
    schedules_df["dep_hour"] = pd.to_datetime(
        schedules_df["departure_time"], format="%H:%M:%S", errors="coerce"
    ).dt.hour.fillna(0).astype(int)

    for sec in trunk_sections:
        sec_id = sec["track_section_id"]
        codes = st_codes_map[sec_id]
        sec_sched = schedules_df[schedules_df["station_code"].isin(codes)]

        hourly_counts = sec_sched.groupby("dep_hour")["train_number"].nunique().to_dict()
        max_hourly = max(hourly_counts.values()) if hourly_counts else 1

        for h in range(24):
            count = hourly_counts.get(h, 0)
            score = round(min(count / max(max_hourly, 1), 1.0), 3)

            if score < 0.30:
                cat = "LOW"
            elif score < 0.70:
                cat = "MEDIUM"
            else:
                cat = "HIGH"

            density_records.append({
                "track_section_id": sec_id,
                "hour_of_day": h,
                "start_time_offset": f"{h:02d}:00:00",
                "end_time_offset": f"{(h+1)%24:02d}:00:00",
                "scheduled_train_count": count,
                "traffic_density_score": score,
                "density_category": cat,
                "derivation_source": "417k_ntes_schedules_aggregation",
            })

    dens_df = pd.DataFrame(density_records)
    dens_df.to_csv(density_out_path, index=False, encoding="utf-8")

    sec_stats = {
        "dataset": "track_sections_processed.csv",
        "rows": len(sec_df),
        "columns": len(sec_df.columns),
        "file_size_bytes": sections_out_path.stat().st_size,
        "duplicates_removed": 0,
        "column_stats": compute_column_stats(sec_df),
    }

    dens_stats = {
        "dataset": "section_traffic_density_processed.csv",
        "rows": len(dens_df),
        "columns": len(dens_df.columns),
        "file_size_bytes": density_out_path.stat().st_size,
        "duplicates_removed": 0,
        "column_stats": compute_column_stats(dens_df),
    }

    return sec_stats, dens_stats


def preprocess_all() -> Dict[str, Any]:
    """Execute complete preprocessing pipeline on all datasets."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    start_time = time.perf_counter()

    results = {}
    results["stations"] = preprocess_stations()
    results["trains"] = preprocess_trains()
    results["schedules"] = preprocess_schedules()

    # Load preprocessed schedules to derive sections and density
    sched_df = pd.read_csv(PROCESSED_DIR / "schedules_processed.csv")
    sec_stats, dens_stats = generate_track_sections_and_density(sched_df)
    results["track_sections"] = sec_stats
    results["traffic_density"] = dens_stats

    summary = {
        "preprocessing_version": "1.0.0",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "total_elapsed_seconds": round(time.perf_counter() - start_time, 2),
        "datasets": results,
    }

    with open(PREPROCESSING_META_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("Preprocessing complete in %.2fs. Metadata saved to %s", summary["total_elapsed_seconds"], PREPROCESSING_META_FILE)
    return summary


if __name__ == "__main__":
    from typing import Tuple
    preprocess_all()
