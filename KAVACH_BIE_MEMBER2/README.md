# KAVACH BIE — Member 2: Advanced AI/ML Train Delay Prediction Module

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests: Pytest](https://img.shields.io/badge/Tests-60%20Passed-brightgreen.svg)](https://docs.pytest.org/)
[![Version: v1.1.0](https://img.shields.io/badge/Release-v1.1.0%20Advanced-orange.svg)](https://github.com/)

An enterprise-ready, modular, leak-free machine learning prediction engine developed for the hackathon project **KAVACH BIE: AI-Based Railway Track Maintenance Block Planning and Delay Prediction System**.

---

## 1. Project Purpose & Target Architecture

In modern railway networks, granting a **maintenance block** (temporary track possession for tamping, rail replacement, OHE overhead wire maintenance, or signaling renewal) suspends regular train dispatch, risking cascading congestion.

### Module Boundaries
- **Member 1 (Data Ingestion)**: Owns authoritative datasets and infrastructure databases.
- **Member 2 (This Module)**: Predicts expected baseline corridor delay, computes scheduled train conflicts, evaluates data quality, and derives the standardized **Maintenance Exposure Score**.
- **Member 3 (Optimization Engine)**: Owns schedule optimization and final maintenance slot selection.
- **Member 4 (Operational Validation)**: Owns signal interlocking, headway verification, and safety certification.
- **Member 5 (Platform & Dashboard)**: Owns the web UI, REST API gateway, and interactive operational dashboard.

```
+---------------------------------------------------------------------------------------+
|                              KAVACH BIE TARGET ARCHITECTURE                           |
|                                                                                       |
|  +--------------------+                                                               |
|  |      MEMBER 1      |                                                               |
|  | Data Management &  |----> Raw Railway Tables                                       |
|  | Ingestion DB       |      (Delays, Schedules, Traffic, Work Orders)                |
|  +--------------------+                         |                                     |
|                                                 v                                     |
|                         +-----------------------------------------------+             |
|                         |         MEMBER 2 (THIS MODULE)                |             |
|                         |    AI/ML Delay & Disruption Prediction Engine |             |
|                         |  - Schema harmonization & Quality Audits      |             |
|                         |  - Leak-free chronological regression         |             |
|                         |  - Timetable overlap analysis                 |             |
|                         |  - Disruption scoring & OOD detection         |             |
|                         |  - Sliced error evaluation (Density/Section)  |             |
|                         +-----------------------------------------------+             |
|                                    |            |           |                         |
|                 +------------------+            |           +-------------------+     |
|                 v                               v                               v     |
|       +--------------------+          +--------------------+          +-------------+ |
|       |      MEMBER 3      |          |      MEMBER 4      |          |  MEMBER 5   | |
|       | Optimization &     |          | Conflict & Safety  |          | Web UI &    | |
|       | Candidate Ranking  |          | Validation Handoff |          | Dashboard   | |
|       +--------------------+          +--------------------+          +-------------+ |
+---------------------------------------------------------------------------------------+
```

### Gap Analysis & Cross-Member Integration Status
- **Current Workspace State**: Modules for Members 1, 3, 4, and 5 are being developed concurrently by teammates.
- **Integration Readiness**: Member 2 provides **dedicated production-style adapters** (`adapters/member1_adapter.py`, `adapters/member3_adapter.py`, `adapters/member4_adapter.py`, `adapters/member5_adapter.py`) and **self-contained simulation mocks** (`adapters/mocks.py`).
- This guarantees zero-dependency standalone execution today, while allowing peers to connect their real modules seamlessly without rewriting the ML engine.

---

## 2. Critical Target Definition & Scientific Honesty

1. **Prediction Target (`predicted_baseline_delay_minutes`)**:
   - Supervised ML regression target is `historical_delay_minutes` — predicting the expected baseline train delay on the corridor under current traffic and schedule load.
2. **Maintenance Exposure Score (`maintenance_exposure_score` / `disruption_score`)**:
   - A multi-factor engineering index combining predicted delay, traffic density, scheduled train overlap, work duration, and priority.
   - **Important Distinction**: The ML model predicts expected corridor delay; it does **not** claim causal attribution for maintenance impact without counterfactual track possession logs.
3. **Synthetic Data Transparency**:
   - All demonstration data is deterministically synthesized (`seed=42`). Evaluation reports are explicitly labeled as synthetic-data benchmarks.

---

## 3. Project Directory Structure

```
KAVACH_BIE_MEMBER2/
├── README.md                      # Complete system documentation & guides
├── requirements.txt               # Pinned Python dependencies
├── .gitignore                     # Git ignore rules for caches & artifacts
├── config.py                      # Dynamic paths, constants, weights, corridor registry
├── generate_data.py               # Deterministic synthetic dataset generator
├── data_validator.py              # Data quality & schema validation logic
├── data_loader.py                 # Data loader with Member 1 schema adapter
├── feature_engineering.py         # Leak-free feature transformers & temporal extractors
├── train_model.py                 # Multi-model training, chronological split, champion selection
├── evaluate_model.py              # Sliced evaluation metrics (Density, Section, Period)
├── predict_delay.py               # Public prediction API & candidate ranking engine
├── prediction_schema.py           # Pydantic data schemas for requests and responses
├── integration_example.py         # Full 6-step cross-module walkthrough
├── api.py                         # Standalone FastAPI integration adapter
├── main.py                        # Master CLI orchestrator (runs full lifecycle)
├── adapters/
│   ├── __init__.py                # Package exports
│   ├── member1_adapter.py         # Upstream ingestion & schema harmonization
│   ├── member3_adapter.py         # Optimization slot ranking & Pareto tradeoffs
│   ├── member4_adapter.py         # Safety & interlocking validation handoff
│   ├── member5_adapter.py         # Dashboard router & endpoint services
│   └── mocks.py                   # Complete mock simulations for Members 1, 3, 4, 5
├── data/
│   ├── sample_train_delays.csv          # 2,100 corridor delay logs
│   ├── sample_train_schedules.csv       # 35 scheduled express & freight services
│   ├── sample_traffic_density.csv       # 1,800 corridor traffic observations
│   └── sample_maintenance_windows.csv   # 13 candidate maintenance block requests
├── models/
│   ├── .gitkeep
│   ├── delay_predictor_pipeline.joblib  # Serialized scikit-learn champion pipeline
│   └── model_metadata.json             # Provenance, hyperparameters & evaluation metrics
├── reports/
│   ├── .gitkeep
│   ├── evaluation_report.json           # Machine-readable test evaluation results
│   ├── evaluation_report.md             # Human-readable Markdown evaluation report
│   └── data_quality_report.json         # Data quality audit report
└── tests/
    ├── test_data_validation.py          # 17 unit tests for validation & edge cases
    ├── test_data_loader.py              # 4 unit tests for data loading & adapters
    ├── test_data_quality.py             # 3 unit tests for quality audits & OOD detection
    ├── test_feature_engineering.py      # 5 unit tests for temporal features & leakage checks
    ├── test_training.py                 # 3 unit tests for training & model persistence
    ├── test_prediction.py               # 6 unit tests for predictions & disruption scoring
    ├── test_integration.py              # 3 integration tests for Member 3 ranking & JSON specs
    ├── test_member1_adapter.py          # 3 unit tests for Member 1 ingestion adapter
    ├── test_member3_adapter.py          # 4 unit tests for Member 3 optimization helper
    ├── test_member4_adapter.py          # 2 unit tests for Member 4 conflict handoff
    ├── test_member5_adapter.py          # 5 unit tests for Member 5 APIRouter endpoints
    └── test_api.py                      # 5 API integration tests for FastAPI server
```

---

## 4. Quick Start Guide (Windows + VS Code)

### Step 1: Open Terminal in Project Folder
```powershell
cd c:\Users\solom\OneDrive\Documents\Desktop\IBMZ\KAVACH_BIE_MEMBER2
```

### Step 2: Activate the Virtual Environment
```powershell
# Using the pre-configured project environment
..\.venv\Scripts\Activate.ps1
```
*(If PowerShell says script execution is disabled, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

### Step 3: Run the Master Workflow
```powershell
python main.py
```
This runs the full lifecycle end-to-end:
1. Validates datasets
2. Trains candidate models and selects the champion
3. Generates evaluation reports in `reports/`
4. Runs a live single-window prediction
5. Runs candidate comparison ranking for Member 3

### Step 4: Run the Automated Tests
```powershell
python -m pytest -v
```
*Result*: **60 passed in 3.40s (100% pass rate)**.

### Step 5: Run Full Team Integration Demo
```powershell
python integration_example.py
```

### Step 6: Start Optional REST API (for Member 5)
```powershell
uvicorn api:app --reload --port 8000
```
Open **`http://127.0.0.1:8000/docs`** in your browser to interact with the API.

---

## 5. Machine Learning Methodology & Error Slicing

### Champion Model Selection
Evaluated on a chronological hold-out test set (420 records across 12 dates):
- `DummyBaseline` (Median): Test MAE = `12.63 mins`, RMSE = `19.60 mins`
- `RidgeRegression` (Selected Champion): Test MAE = **`10.87 mins`** (14.0% improvement over baseline), RMSE = **`16.48 mins`**, $R^2 = 0.2001$
- `RandomForest`: Test MAE = `11.58 mins`, RMSE = `17.30 mins`
- `GradientBoosting`: Test MAE = `11.45 mins`, RMSE = `17.60 mins`

### Sliced Error Analysis (from `reports/evaluation_report.md`)
To evaluate performance stability, errors are broken down across operational slices:

#### A. By Corridor Traffic Density Level
| Traffic Level | Test Samples | MAE (mins) | RMSE (mins) | Operational Note |
|:---|:---:|:---:|:---:|:---|
| `LOW (<0.60)` | 179 | **6.29** | 8.12 | Standard operations / night hours |
| `MEDIUM (0.60-0.85)` | 88 | **11.44** | 17.66 | Moderate headway compression |
| `HIGH (>0.85)` | 153 | **15.89** | 22.12 | Heavy congestion / peak dispatch |

#### B. By Track Section Corridor
| Track Section | Corridor Name | Test Samples | MAE (mins) | RMSE (mins) |
|:---|:---|:---:|:---:|:---:|
| `SEC_GKP_BST` | Gorakhpur - Basti (Regional) | 60 | **6.98** | 8.62 |
| `SEC_CNB_PRYJ` | Kanpur - Prayagraj | 60 | **7.35** | 10.96 |
| `SEC_HWH_ASN` | Howrah - Asansol | 72 | **9.86** | 13.31 |
| `SEC_SBC_MAS` | Bengaluru - Chennai | 60 | **10.08** | 17.01 |
| `SEC_BCT_ST` | Mumbai Central - Surat | 84 | **13.16** | 20.66 |
| `SEC_NDLS_CNB` | New Delhi - Kanpur (Trunk) | 84 | **15.29** | 20.84 |

#### C. By Operational Time Period
| Time Period | Test Samples | MAE (mins) | RMSE (mins) |
|:---|:---:|:---:|:---:|
| `NIGHT` (00:00 - 06:00) | 96 | **4.83** | 6.52 |
| `LATE_NIGHT` (22:00 - 24:00) | 36 | **7.98** | 10.14 |
| `AFTERNOON` (11:00 - 17:00) | 72 | **8.65** | 12.20 |
| `PEAK_EVENING` (17:00 - 22:00) | 84 | **13.87** | 20.52 |
| `PEAK_MORNING` (06:00 - 11:00) | 132 | **15.34** | 21.36 |

---

## 6. Disruption Score & Risk Classification

### The Disruption Score Formula

$$\text{Disruption Score} = \left[ (\text{Delay} \times 0.35) + (\text{Density} \times 20 \times 0.25) + (\text{AffectedTrains} \times 10 \times 0.25) + \left(\frac{\text{Duration}}{60} \times 5 \times 0.15\right) \right] \times \text{PriorityMultiplier}$$

- **Priority Multiplier**: `CRITICAL` (1.25), `HIGH` (1.15), `MEDIUM` (1.00), `LOW` (0.85).
- **Risk Tiers**:
  - `LOW`: $0.0 \le \text{Score} < 25.0$ (Minimal network impact)
  - `MEDIUM`: $25.0 \le \text{Score} < 50.0$ (Moderate impact)
  - `HIGH`: $50.0 \le \text{Score} < 75.0$ (High congestion risk)
  - `CRITICAL`: $\text{Score} \ge 75.0$ (Severe corridor bottleneck)

---

## 7. Instructions for Peer Team Members

### For Member 1 (Data Ingestion)
Import `Member1DataAdapter` to harmonize raw CSV/DB exports:
```python
from adapters.member1_adapter import Member1DataAdapter

adapter = Member1DataAdapter()
# Ingest raw external data with non-standard column names
clean_df, validation_result = adapter.harmonize_and_validate_delays(raw_delays_df)
print(f"Validated {len(clean_df)} records. Dropped {validation_result.rows_rejected} bad rows.")
```

### For Member 3 (Optimization Engine)
Import `Member3OptimizationAdapter` to evaluate and rank candidate slots:
```python
from adapters.member3_adapter import Member3OptimizationAdapter

# 1. Compare and rank multiple candidate slots (infeasible slots preserved with diagnostics)
ranking = Member3OptimizationAdapter.rank_candidate_slots(candidate_windows)
print("Optimal Window:", ranking["recommended_request_id"])

# 2. Compute Pareto trade-off between Disruption vs. Work Duration
pareto = Member3OptimizationAdapter.compute_pareto_tradeoffs(candidate_windows)
```

### For Member 4 (Operational Conflict Validation)
Import `Member4ValidationAdapter` to extract safety handoff context:
```python
from adapters.member4_adapter import Member4ValidationAdapter

payload = Member4ValidationAdapter.get_validation_payload(request)
print(f"Conflicting Trains Overlapping Window: {payload.affected_train_count}")
for train in payload.conflicting_trains:
    print(f" - Train {train['train_number']}: {train['scheduled_arrival']} -> {train['scheduled_departure']}")
```

### For Member 5 (Web UI & Dashboard)
Mount the Member 5 APIRouter directly into your main FastAPI application:
```python
from fastapi import FastAPI
from adapters.member5_adapter import get_member5_router

app = FastAPI(title="KAVACH BIE Unified Backend")
app.include_router(get_member5_router(), prefix="/api/v1/delays")
```

---

## 8. Automated Test Summary

**60 automated tests execute and pass in 3.4 seconds:**
```
tests/test_api.py::TestFastAPIEndpoints .................... [  8%]
tests/test_data_loader.py::TestDataLoader .................. [ 15%]
tests/test_data_quality.py::TestDataQualityAudit ........... [ 20%]
tests/test_data_validation.py::TestTimeParsingHelpers ...... [ 25%]
tests/test_data_validation.py::TestDelaysValidation ........ [ 35%]
tests/test_data_validation.py::TestSchedulesValidation ..... [ 38%]
tests/test_data_validation.py::TestMaintenanceRequest ...... [ 48%]
tests/test_feature_engineering.py .......................... [ 56%]
tests/test_integration.py .................................. [ 61%]
tests/test_member1_adapter.py .............................. [ 66%]
tests/test_member3_adapter.py .............................. [ 73%]
tests/test_member4_adapter.py .............................. [ 76%]
tests/test_member5_adapter.py .............................. [ 85%]
tests/test_prediction.py ................................... [ 95%]
tests/test_training.py ..................................... [100%]

======================== 60 passed in 3.40s ========================
```
