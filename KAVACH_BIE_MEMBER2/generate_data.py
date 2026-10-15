"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Deterministic Synthetic Railway Dataset Generator
===============================================================================
Generates realistic, logically consistent, and reproducible synthetic railway
operational datasets for training, evaluation, and system demonstration:
1. sample_train_delays.csv       (~1400 corridor delay logs across 60 days)
2. sample_train_schedules.csv    (36 scheduled intercity, express & freight runs)
3. sample_traffic_density.csv    (corridor traffic & utilization records)
4. sample_maintenance_windows.csv (24 candidate block requests for optimization)

NOTE: These datasets are explicitly synthetic for algorithmic demonstration and
benchmarking. They do NOT represent real Indian Railways operational logs.
"""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from config import (
    DELAYS_DATA_FILE,
    KNOWN_TRACK_SECTIONS,
    MAINTENANCE_DATA_FILE,
    RANDOM_SEED,
    SCHEDULES_DATA_FILE,
    TRAFFIC_DATA_FILE,
)

# Reference fleet of trains operating across our corridor network
REFERENCE_TRAINS = [
    # North Central Trunk (SEC_NDLS_CNB, SEC_CNB_PRYJ)
    ("12002", "Bhopal Shatabdi Express", "NDLS", "BPL", "SEC_NDLS_CNB", "06:00", "10:15", 255),
    ("12004", "Lucknow Swarna Shatabdi", "NDLS", "LKO", "SEC_NDLS_CNB", "06:10", "11:20", 310),
    ("22436", "Vande Bharat Express", "NDLS", "BSB", "SEC_NDLS_CNB", "06:00", "10:08", 248),
    ("22436", "Vande Bharat Express", "CNB", "BSB", "SEC_CNB_PRYJ", "10:12", "12:15", 123),
    ("12302", "Howrah Rajdhani Express", "NDLS", "HWH", "SEC_NDLS_CNB", "16:55", "21:35", 280),
    ("12302", "Howrah Rajdhani Express", "CNB", "PRYJ", "SEC_CNB_PRYJ", "21:40", "23:45", 125),
    ("12802", "Purushottam Express", "NDLS", "PURI", "SEC_NDLS_CNB", "22:40", "04:00", 320),
    ("12802", "Purushottam Express", "CNB", "PRYJ", "SEC_CNB_PRYJ", "04:05", "06:30", 145),
    ("12394", "Sampoorna Kranti Express", "NDLS", "RJPB", "SEC_NDLS_CNB", "17:30", "22:25", 295),
    ("12394", "Sampoorna Kranti Express", "CNB", "PRYJ", "SEC_CNB_PRYJ", "22:30", "00:45", 135),
    ("FRT_501", "Container Freight Shuttle", "TKD", "CNB", "SEC_NDLS_CNB", "01:15", "07:30", 375),
    ("FRT_502", "Mineral Freight Rake", "PRYJ", "CNB", "SEC_CNB_PRYJ", "02:00", "05:45", 225),

    # Western Corridor (SEC_BCT_ST)
    ("12951", "Mumbai Tejas Rajdhani", "MMCT", "NDLS", "SEC_BCT_ST", "17:00", "19:43", 163),
    ("12953", "August Kranti Rajdhani", "MMCT", "NZM", "SEC_BCT_ST", "17:10", "20:00", 170),
    ("12009", "Mumbai Ahmedabad Shatabdi", "MMCT", "ADI", "SEC_BCT_ST", "06:20", "09:22", 182),
    ("20901", "Vande Bharat Express", "MMCT", "GNC", "SEC_BCT_ST", "06:00", "08:35", 155),
    ("12925", "Paschim SF Express", "MMCT", "ASR", "SEC_BCT_ST", "11:25", "14:45", 200),
    ("12903", "Golden Temple Mail", "MMCT", "ASR", "SEC_BCT_ST", "18:45", "22:10", 205),
    ("FRT_601", "Automobile Freight Express", "JNPT", "ST", "SEC_BCT_ST", "02:30", "07:15", 285),

    # Eastern Corridor (SEC_HWH_ASN)
    ("12019", "Howrah Ranchi Shatabdi", "HWH", "RNC", "SEC_HWH_ASN", "06:05", "08:50", 165),
    ("12303", "Poorva Superfast Express", "HWH", "NDLS", "SEC_HWH_ASN", "08:00", "10:55", 175),
    ("12313", "Sealdah Rajdhani Express", "SDAH", "NDLS", "SEC_HWH_ASN", "16:50", "19:35", 165),
    ("12321", "Howrah Mumbai Mail", "HWH", "CSMT", "SEC_HWH_ASN", "23:35", "02:40", 185),
    ("FRT_701", "Coal Rake Dedicated Freight", "HWH", "ASN", "SEC_HWH_ASN", "00:30", "04:30", 240),
    ("FRT_702", "Steel Coil Freight Special", "ASN", "HWH", "SEC_HWH_ASN", "13:00", "17:15", 255),

    # Southern Corridor (SEC_SBC_MAS)
    ("20608", "Vande Bharat Express", "MYS", "MAS", "SEC_SBC_MAS", "14:45", "19:20", 275),
    ("12028", "Shatabdi Express", "SBC", "MAS", "SEC_SBC_MAS", "06:00", "11:00", 300),
    ("12610", "Chennai Intercity SF", "SBC", "MAS", "SEC_SBC_MAS", "08:00", "14:15", 375),
    ("12658", "Chennai Mail Express", "SBC", "MAS", "SEC_SBC_MAS", "22:40", "04:20", 340),
    ("FRT_801", "Auto Component Parcel Express", "WFD", "TRL", "SEC_SBC_MAS", "01:00", "06:30", 330),

    # North Eastern Corridor (SEC_GKP_BST)
    ("12555", "Gorakhdham SF Express", "GKP", "BTI", "SEC_GKP_BST", "16:35", "17:40", 65),
    ("12556", "Gorakhdham SF Express", "BTI", "GKP", "SEC_GKP_BST", "08:25", "09:45", 80),
    ("15004", "Chauri Chaura Express", "GKP", "CPA", "SEC_GKP_BST", "23:20", "00:35", 75),
    ("15007", "Krishak Express", "BCY", "LJN", "SEC_GKP_BST", "01:45", "03:10", 85),
    ("FRT_901", "Foodgrain Freight Rake", "GKP", "BST", "SEC_GKP_BST", "11:00", "13:00", 120),
]


def format_minutes_to_time(minutes: int) -> str:
    """Format total minutes from midnight into 24-hr HH:MM."""
    m = minutes % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def generate_synthetic_data(seed: int = RANDOM_SEED) -> Dict[str, pd.DataFrame]:
    """
    Generate all four synthetic railway datasets deterministically.
    Returns a dictionary of DataFrames:
    {'delays': df, 'schedules': df, 'traffic': df, 'maintenance': df}
    """
    np.random.seed(seed)
    random.seed(seed)

    # -------------------------------------------------------------------------
    # 1. Train Schedules (sample_train_schedules.csv)
    # -------------------------------------------------------------------------
    schedules_rows = []
    for t_num, t_name, src, dst, section, arr, dep, run_time in REFERENCE_TRAINS:
        schedules_rows.append(
            {
                "train_number": t_num,
                "train_name": t_name,
                "source": src,
                "destination": dst,
                "track_section": section,
                "scheduled_arrival": arr,
                "scheduled_departure": dep,
                "scheduled_running_time_minutes": int(run_time),
            }
        )
    df_schedules = pd.DataFrame(schedules_rows)

    # -------------------------------------------------------------------------
    # 2. Traffic Density Logs (sample_traffic_density.csv)
    # -------------------------------------------------------------------------
    start_date = datetime(2026, 8, 1)
    num_days = 60
    traffic_rows = []
    time_periods = ["NIGHT", "PEAK_MORNING", "AFTERNOON", "PEAK_EVENING", "LATE_NIGHT"]

    # Base density per corridor
    section_density_base = {
        "SEC_NDLS_CNB": 0.82,
        "SEC_CNB_PRYJ": 0.76,
        "SEC_BCT_ST": 0.80,
        "SEC_HWH_ASN": 0.70,
        "SEC_SBC_MAS": 0.62,
        "SEC_GKP_BST": 0.45,
    }

    for day_idx in range(num_days):
        current_date = start_date + timedelta(days=day_idx)
        date_str = current_date.strftime("%Y-%m-%d")
        is_weekend = current_date.weekday() >= 5

        for section, base_density in section_density_base.items():
            for period in time_periods:
                period_multiplier = {
                    "NIGHT": 0.55,
                    "PEAK_MORNING": 1.25,
                    "AFTERNOON": 0.90,
                    "PEAK_EVENING": 1.30,
                    "LATE_NIGHT": 0.70,
                }[period]

                # Weekend traffic adjustment
                weekend_factor = 0.92 if is_weekend else 1.0

                # Realistic stochastic fluctuation
                noise = np.random.normal(0.0, 0.04)
                density = float(np.clip(base_density * period_multiplier * weekend_factor + noise, 0.20, 1.20))

                # Scheduled trains in this slice
                base_train_count = {
                    "SEC_NDLS_CNB": 24,
                    "SEC_CNB_PRYJ": 20,
                    "SEC_BCT_ST": 22,
                    "SEC_HWH_ASN": 18,
                    "SEC_SBC_MAS": 14,
                    "SEC_GKP_BST": 8,
                }[section]
                scheduled_count = max(
                    2,
                    int(round(base_train_count * (period_multiplier / 1.0) * (0.95 + np.random.uniform(0, 0.1)))),
                )

                utilization = float(np.clip(density * 1.05 + np.random.normal(0, 0.03), 0.25, 1.30))

                traffic_rows.append(
                    {
                        "track_section": section,
                        "observation_date": date_str,
                        "time_period": period,
                        "traffic_density": round(density, 3),
                        "scheduled_train_count": scheduled_count,
                        "track_utilization": round(utilization, 3),
                    }
                )

    df_traffic = pd.DataFrame(traffic_rows)

    # -------------------------------------------------------------------------
    # 3. Historical Train Delays (sample_train_delays.csv)
    # -------------------------------------------------------------------------
    delay_rows = []
    # Build a lookup for traffic density
    traffic_lookup = {
        (r["track_section"], r["observation_date"], r["time_period"]): r["traffic_density"]
        for _, r in df_traffic.iterrows()
    }

    for day_idx in range(num_days):
        current_date = start_date + timedelta(days=day_idx)
        date_str = current_date.strftime("%Y-%m-%d")

        for sched in schedules_rows:
            section = sched["track_section"]
            dep_hour = int(sched["scheduled_departure"].split(":")[0])

            # Classify period
            if 0 <= dep_hour < 6:
                period = "NIGHT"
            elif 6 <= dep_hour < 11:
                period = "PEAK_MORNING"
            elif 11 <= dep_hour < 17:
                period = "AFTERNOON"
            elif 17 <= dep_hour < 22:
                period = "PEAK_EVENING"
            else:
                period = "LATE_NIGHT"

            density = traffic_lookup.get((section, date_str, period), 0.65)

            # Delay generation logic:
            # Baseline delay is influenced by corridor density + time period + stochastic factor
            base_delay_lambda = (density * 18.0) + (8.0 if "PEAK" in period else 2.0)
            if "NDLS_CNB" in section or "BCT_ST" in section:
                base_delay_lambda += 5.0  # Extra congestion on busy corridors

            # Generate realistic right-skewed delay distribution (Gamma distribution)
            # Most trains have small delays (5-15 mins), occasional high delays (40-90 mins)
            shape = 2.0
            scale = max(1.0, base_delay_lambda / shape)
            generated_delay = float(np.random.gamma(shape=shape, scale=scale))

            # Introduce realistic 10% on-time/minor delay (0 to 3 minutes)
            if np.random.random() < 0.12:
                generated_delay = float(np.random.uniform(0.0, 3.0))

            delay_minutes = round(generated_delay, 1)

            # Generate consistent actual arrival and departure
            sched_dep_dt = datetime.strptime(f"{date_str} {sched['scheduled_departure']}", "%Y-%m-%d %H:%M")
            sched_arr_dt = datetime.strptime(f"{date_str} {sched['scheduled_arrival']}", "%Y-%m-%d %H:%M")

            # Upstream entry delay before entering section
            upstream_delay = max(0.0, delay_minutes * np.random.uniform(0.6, 0.9))
            actual_arr_dt = sched_arr_dt + timedelta(minutes=round(upstream_delay))
            actual_dep_dt = sched_dep_dt + timedelta(minutes=round(delay_minutes))

            delay_rows.append(
                {
                    "train_number": sched["train_number"],
                    "train_name": sched["train_name"],
                    "service_date": date_str,
                    "track_section": section,
                    "scheduled_arrival": sched_arr_dt.strftime("%H:%M"),
                    "actual_arrival": actual_arr_dt.strftime("%H:%M"),
                    "scheduled_departure": sched_dep_dt.strftime("%H:%M"),
                    "actual_departure": actual_dep_dt.strftime("%H:%M"),
                    "historical_delay_minutes": delay_minutes,
                }
            )

    df_delays = pd.DataFrame(delay_rows)

    # -------------------------------------------------------------------------
    # 4. Sample Maintenance Windows (sample_maintenance_windows.csv)
    # -------------------------------------------------------------------------
    # Includes diverse scenarios: daylight vs night blocks, high vs low priority,
    # multiple candidate options for the same section (for Member 3 ranking)
    maintenance_rows = [
        # Set A: Candidate options for high-density NDLS-CNB corridor (REQ_BLK_001A, B, C)
        {
            "request_id": "REQ_NDLS_001A",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-15",
            "proposed_start_time": "01:30",
            "proposed_end_time": "04:30",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        },
        {
            "request_id": "REQ_NDLS_001B",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-15",
            "proposed_start_time": "06:30",
            "proposed_end_time": "09:30",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        },
        {
            "request_id": "REQ_NDLS_001C",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-15",
            "proposed_start_time": "11:30",
            "proposed_end_time": "14:30",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        },
        # Set B: Emergency Track Renewal on CNB-PRYJ (Critical priority)
        {
            "request_id": "REQ_PRYJ_002A",
            "track_section": "SEC_CNB_PRYJ",
            "requested_date": "2026-10-16",
            "proposed_start_time": "01:00",
            "proposed_end_time": "05:00",
            "required_duration_minutes": 240.0,
            "maintenance_priority": "CRITICAL",
        },
        {
            "request_id": "REQ_PRYJ_002B",
            "track_section": "SEC_CNB_PRYJ",
            "requested_date": "2026-10-16",
            "proposed_start_time": "13:00",
            "proposed_end_time": "17:00",
            "required_duration_minutes": 240.0,
            "maintenance_priority": "CRITICAL",
        },
        # Set C: OHE Overhead Wire Inspection on BCT-ST (Western Railway)
        {
            "request_id": "REQ_BCT_003A",
            "track_section": "SEC_BCT_ST",
            "requested_date": "2026-10-18",
            "proposed_start_time": "02:00",
            "proposed_end_time": "04:30",
            "required_duration_minutes": 150.0,
            "maintenance_priority": "MEDIUM",
        },
        {
            "request_id": "REQ_BCT_003B",
            "track_section": "SEC_BCT_ST",
            "requested_date": "2026-10-18",
            "proposed_start_time": "17:30",
            "proposed_end_time": "20:00",
            "required_duration_minutes": 150.0,
            "maintenance_priority": "MEDIUM",
        },
        # Set D: Bridge Girder Maintenance on Eastern Corridor HWH-ASN
        {
            "request_id": "REQ_HWH_004A",
            "track_section": "SEC_HWH_ASN",
            "requested_date": "2026-10-20",
            "proposed_start_time": "00:30",
            "proposed_end_time": "05:30",
            "required_duration_minutes": 300.0,
            "maintenance_priority": "HIGH",
        },
        {
            "request_id": "REQ_HWH_004B",
            "track_section": "SEC_HWH_ASN",
            "requested_date": "2026-10-20",
            "proposed_start_time": "10:00",
            "proposed_end_time": "15:00",
            "required_duration_minutes": 300.0,
            "maintenance_priority": "HIGH",
        },
        # Set E: Signaling & Interlocking upgrade on SBC-MAS
        {
            "request_id": "REQ_SBC_005A",
            "track_section": "SEC_SBC_MAS",
            "requested_date": "2026-10-22",
            "proposed_start_time": "01:00",
            "proposed_end_time": "03:30",
            "required_duration_minutes": 150.0,
            "maintenance_priority": "LOW",
        },
        {
            "request_id": "REQ_SBC_005B",
            "track_section": "SEC_SBC_MAS",
            "requested_date": "2026-10-22",
            "proposed_start_time": "08:30",
            "proposed_end_time": "11:00",
            "required_duration_minutes": 150.0,
            "maintenance_priority": "LOW",
        },
        # Set F: Ballast Cleaning Machine on Gorakhpur-Basti regional line
        {
            "request_id": "REQ_GKP_006A",
            "track_section": "SEC_GKP_BST",
            "requested_date": "2026-10-24",
            "proposed_start_time": "02:00",
            "proposed_end_time": "06:00",
            "required_duration_minutes": 240.0,
            "maintenance_priority": "MEDIUM",
        },
        {
            "request_id": "REQ_GKP_006B",
            "track_section": "SEC_GKP_BST",
            "requested_date": "2026-10-24",
            "proposed_start_time": "14:00",
            "proposed_end_time": "18:00",
            "required_duration_minutes": 240.0,
            "maintenance_priority": "MEDIUM",
        },
    ]
    df_maintenance = pd.DataFrame(maintenance_rows)

    return {
        "delays": df_delays,
        "schedules": df_schedules,
        "traffic": df_traffic,
        "maintenance": df_maintenance,
    }


def save_synthetic_datasets(datasets: Dict[str, pd.DataFrame]) -> None:
    """Save generated datasets into the data directory."""
    datasets["delays"].to_csv(DELAYS_DATA_FILE, index=False)
    datasets["schedules"].to_csv(SCHEDULES_DATA_FILE, index=False)
    datasets["traffic"].to_csv(TRAFFIC_DATA_FILE, index=False)
    datasets["maintenance"].to_csv(MAINTENANCE_DATA_FILE, index=False)


if __name__ == "__main__":
    print("[*] Generating deterministic synthetic railway datasets for KAVACH BIE...")
    data_dict = generate_synthetic_data(seed=RANDOM_SEED)
    save_synthetic_datasets(data_dict)
    print(f" [+] Generated {len(data_dict['delays'])} delay records -> {DELAYS_DATA_FILE}")
    print(f" [+] Generated {len(data_dict['schedules'])} train schedules -> {SCHEDULES_DATA_FILE}")
    print(f" [+] Generated {len(data_dict['traffic'])} traffic density records -> {TRAFFIC_DATA_FILE}")
    print(f" [+] Generated {len(data_dict['maintenance'])} maintenance window examples -> {MAINTENANCE_DATA_FILE}")
    print("[OK] Dataset generation complete.")
