# KAVACH BIE — Member 3: AI Block Planning and Optimization Engine

> **Project:** KAVACH BIE (Block Intelligence Engine)  
> **Problem Statement:** SIH26027 (Railway Maintenance Block Scheduling)  
> **Assigned Role:** Member 3 — Core Optimization Algorithm & Constraint Engine  
> **Technology Stack:** Python 3.10+, Google OR-Tools CP-SAT, Pandas, NumPy, Pydantic v2, FastAPI, Pytest  

---

## 1. System Overview

**Member 3** is the mathematical reasoning and constraint-optimization core of **KAVACH BIE**. Its primary objective is to recommend conflict-free, minimal-disruption railway maintenance block windows by synthesizing train timetables, track section traffic density, resource availability, section blockouts, disruption delay estimates (from Member 2), and operational validation (from Member 4).

### Key Responsibilities:
1. **Request Validation:** Strict domain validation of maintenance block requests (planning horizon, durations, priorities, resource requests).
2. **Candidate Window Generation:** Discrete temporal shifting (e.g., 15m or 30m steps) adhering to earliest start, latest end, and midnight/multi-day crossing boundaries.
3. **Candidate Evaluation:** Vectorized train overlap detection, traffic density lookups, resource calendar checks, and disruption prediction.
4. **Constraint Programming (Google OR-Tools CP-SAT):** Mathematical integer constraint modeling separating mandatory hard constraints from soft multi-criteria trade-offs.
5. **Interactive Conflict Validation with Member 4:** Automated iterative submission loop with fallback to ranked alternatives upon detection of operational conflicts.
6. **Transparent Explainability:** Natural-language justifications, component scoring breakdowns, and ranked feasible alternatives.
7. **FastAPI Backend Integration for Member 5:** Out-of-the-box APIRouter mountable directly into Member 5's main application.

---

## 2. Mathematical Formulation & Algorithm

The engine models maintenance block scheduling as an exact **Constraint Satisfaction & Multi-Objective Optimization Problem** solved via **Google OR-Tools CP-SAT**.

### 2.1 Decision Variables
For a candidate set of windows $\mathcal{C} = \{c_1, c_2, \dots, c_N\}$ generated within the planning horizon:
$$x_i \in \{0, 1\} \quad \forall i \in \{1, \dots, N\}$$
where $x_i = 1$ if window candidate $c_i$ is selected, and $0$ otherwise.

### 2.2 Hard Constraints
1. **Single-Request Feasibility:**
   $$\sum_{i \in \text{Feasible}} x_i = 1$$
2. **Infeasibility Invalidation:**
   $$x_i = 0 \quad \forall i \notin \text{Feasible}$$
   A candidate $c_i$ is infeasible if any of the following are violated:
   - **Duration:** $\text{duration}(c_i) < \text{duration}_{\text{required}}$
   - **Planning Horizon:** $\text{start}(c_i) < T_{\text{start}}$ or $\text{end}(c_i) > T_{\text{end}}$
   - **Restricted Boundaries:** $\text{start}(c_i) < T_{\text{earliest}}$ or $\text{end}(c_i) > T_{\text{latest}}$
   - **Resource Unavailability:** Required resource crew/equipment unavailable during $[\text{start}(c_i), \text{end}(c_i)]$
   - **Section Unavailability:** Track section is closed or has pre-approved maintenance blocks during $[\text{start}(c_i), \text{end}(c_i)]$
3. **Disjunctive Section Non-Overlap (Multi-Request Joint Mode):**
   If requests $R_a$ and $R_b$ both request section $S$, and windows $c_{a,i}$ and $c_{b,j}$ temporally overlap:
   $$x_{a,i} + x_{b,j} \le 1$$

### 2.3 Multi-Objective Cost Function
Candidate evaluation computes a normalized composite penalty score $S_i \in [0.0, 1.0]$:
$$S_i = w_{\text{delay}} \cdot \bar{D}_i + w_{\text{trains}} \cdot \bar{T}_i + w_{\text{density}} \cdot \bar{\rho}_i + w_{\text{slack}} \cdot \bar{\sigma}_i + w_{\text{urgency}} \cdot \bar{U}_i$$

- **Normalized Delay ($\bar{D}_i$):** $\min(D_i / D_{\text{ref}}, 1.0)$
- **Normalized Affected Trains ($\bar{T}_i$):** $\min(T_i / T_{\text{ref}}, 1.0)$
- **Normalized Traffic Density ($\bar{\rho}_i$):** Average section traffic density $\in [0.0, 1.0]$
- **Normalized Slack ($\bar{\sigma}_i$):** $(\text{duration}_i - \text{duration}_{\text{req}}) / 60.0$
- **Urgency ($\bar{U}_i$):** Scaled offset into horizon weighted by maintenance priority ($\text{EMERGENCY} = 1.0, \text{HIGH} = 0.6, \text{MEDIUM} = 0.3, \text{LOW} = 0.0$)

**Integer CP-SAT Translation:**
$$\min \sum_{i \in \text{Feasible}} \text{round}(10,000 \cdot S_i) \cdot x_i$$

---

## 3. Architecture & File Structure

```
├── optimizer/
│   ├── __init__.py               # Package exports & public API
│   ├── schemas.py                # Pydantic v2 data models & validation
│   ├── exceptions.py             # Structured domain exceptions
│   ├── data_adapter.py           # Ingestion, normalization & prediction adapter
│   ├── candidate_generator.py    # Temporal window generation logic
│   ├── candidate_evaluator.py    # Overlaps, density, & constraint checks
│   ├── objective.py              # Multi-factor normalized cost scoring
│   ├── optimizer_engine.py       # Google OR-Tools CP-SAT solver
│   ├── validation_client.py      # Member 4 conflict validation adapter & mock
│   ├── service.py                # End-to-end workflow orchestration
│   └── api.py                    # FastAPI APIRouter for Member 5 backend
├── data/synthetic/
│   ├── train_schedule.csv        # Realistic scheduled train movements
│   ├── traffic_density.csv       # Hourly section traffic density
│   ├── maintenance_requests.csv  # Sample maintenance requests
│   ├── resource_availability.csv # Crew & machinery calendars
│   ├── section_availability.csv  # Section closures & pre-approved blocks
│   └── historical_delays.csv     # Synthetic historical delay records
├── tests/
│   ├── conftest.py               # Shared test fixtures & timezones
│   ├── test_schemas.py           # Pydantic model validation tests
│   ├── test_candidate_generator.py# Generator step & boundary tests
│   ├── test_candidate_evaluator.py# Overlap & constraint evaluation tests
│   ├── test_optimizer_engine.py  # OR-Tools CP-SAT solver & joint tests
│   ├── test_validation_client.py # Member 4 validation client tests
│   ├── test_service_end_to_end.py# All 15 required scenarios
│   └── test_api.py               # FastAPI endpoint tests
├── demo_runner.py                # Standalone demonstration script
├── demo_input.json               # Sample input request
├── demo_output.json              # Sample optimization response
├── requirements.txt              # Production and test dependencies
└── README_MEMBER3.md             # Complete module documentation
```

---

## 4. Inter-Member Interfaces & Integration

### 4.1 Member 1 (Data Ingestion & Store)
Member 3 ingests data via `DataLoader` in `optimizer/data_adapter.py`. It accepts CSV file paths, Pandas DataFrames, or raw dictionaries:
- `DataLoader.load_train_schedules(...)`
- `DataLoader.load_traffic_density(...)`
- `DataLoader.load_resource_availability(...)`
- `DataLoader.load_section_availability(...)`

### 4.2 Member 2 (Delay & Disruption Prediction Engine)
Member 3 defines a pluggable interface:
```python
from optimizer.data_adapter import DelayPredictorInterface, Member2PredictorAdapter

class Member2DelayPredictor(DelayPredictorInterface):
    def predict_disruption(self, candidate_window, train_data, traffic_data):
        # Call Member 2's trained ML model or microservice
        return DisruptionPrediction(...)

# Wrap in adapter:
adapter = Member2PredictorAdapter(predictor_callable=my_member2_func)
```
*Note:* A calibrated baseline estimator (`BaselineDelayPredictor`) is provided for local execution and testing. It calculates realistic secondary delays based on train types (Rajdhani, Freight, Express), priority weights, and density multipliers.

### 4.3 Member 4 (Conflict Detection & Operational Validation Engine)
Member 3 enforces an automated validation loop:
1. OR-Tools selects the optimal candidate.
2. The candidate is sent to Member 4 via `ConflictValidationInterface` / `Member4HTTPClient`.
3. If `VALID`: Window is recommended.
4. If `CONFLICT`: Conflict reason is logged, candidate is marked rejected, and the next-best ranked alternative is submitted.
5. If all candidates fail validation: Status `NO_FEASIBLE_WINDOW` is returned.

### 4.4 Member 5 (FastAPI Web Backend Integration)
Mount Member 3's router directly inside Member 5's main FastAPI app:
```python
from fastapi import FastAPI
from optimizer.api import optimizer_router

app = FastAPI(title="KAVACH BIE")
app.include_router(optimizer_router)
```
Endpoint exposed: `POST /api/optimization/recommend`.

---

## 5. Installation and Execution

### 5.1 Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- pip package manager

### 5.2 Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 5.3 Run All Automated Tests
To run the full test suite (43 tests covering all 15 scenarios, schemas, solver, and API):
```powershell
python -m pytest -v
```

### 5.4 Run the Standalone Demo
```powershell
python demo_runner.py
```
This loads synthetic datasets, runs the optimization loop, prints formatted recommendations, and outputs `demo_input.json` and `demo_output.json`.

### 5.5 Run the FastAPI Microservice
```powershell
python -m uvicorn optimizer.api:app --reload --port 8003
```
Interactive Swagger docs available at: `http://localhost:8003/docs`

---

## 6. API Request & Response Contracts

### Sample Input Payload (`POST /api/optimization/recommend`):
```json
{
  "request_id": "MR-DEMO-001",
  "track_section_id": "SEC-01",
  "planning_start": "2026-10-15T08:00:00+05:30",
  "planning_end": "2026-10-15T18:00:00+05:30",
  "required_duration_minutes": 60,
  "maintenance_priority": "HIGH",
  "required_resources": [
    "TRACK_TEAM_A"
  ],
  "earliest_start_time": "2026-10-15T09:00:00+05:30",
  "latest_end_time": "2026-10-15T17:00:00+05:30"
}
```

### Generated Output Response:
```json
{
  "status": "RECOMMENDED",
  "request_id": "MR-DEMO-001",
  "recommendation": {
    "track_section_id": "SEC-01",
    "start_time": "2026-10-15T11:00:00+05:30",
    "end_time": "2026-10-15T12:00:00+05:30",
    "duration_minutes": 60
  },
  "estimated_impact": {
    "affected_train_count": 0,
    "predicted_delay_minutes": 0.45,
    "traffic_density": 0.15,
    "affected_trains": []
  },
  "validation": {
    "status": "VALID",
    "reason": "No operational headway or interlocking conflicts detected by Member 4 validator.",
    "validator_used": "MockMember4Validator",
    "validation_attempts": 1
  },
  "alternatives": [
    {
      "rank": 1,
      "candidate_id": "CW-010",
      "start_time": "2026-10-15T11:15:00+05:30",
      "end_time": "2026-10-15T12:15:00+05:30",
      "duration_minutes": 60,
      "objective_score": 0.045,
      "affected_train_count": 0,
      "predicted_delay_minutes": 0.45,
      "traffic_density": 0.15,
      "validation_status": "VALIDATION_PENDING"
    }
  ],
  "rejected_candidates": [],
  "explanation": [
    "Recommended maintenance block on section SEC-01 from 2026-10-15 11:00 to 2026-10-15 12:00 (60 minutes).",
    "Optimization score is 0.0435 (predicted disruption delay: 0.5 mins, affected trains: 0, traffic density: 0.15).",
    "Candidate CW-009 (11:00-12:00) passed operational validation.",
    "Solution mathematically proven OPTIMAL by Google OR-Tools CP-SAT in 0.004s."
  ],
  "solver": {
    "status": "OPTIMAL",
    "objective_score": 0.0435,
    "wall_time_seconds": 0.0044,
    "is_optimal": true
  }
}
```

---

## 7. Status Reference & Error Diagnostics

| Status | Meaning | Action Taken |
| :--- | :--- | :--- |
| `RECOMMENDED` | Optimal candidate found, passes all hard constraints, and validated by Member 4. | Primary schedule recommendation ready. |
| `NO_FEASIBLE_WINDOW` | All generated candidates violate hard constraints or were rejected by Member 4. | Explanation lists specific violation reasons. |
| `INVALID_REQUEST` | Input schema validation failed (e.g., negative duration, inverted timestamps). | Request rejected prior to solver execution. |
| `PREDICTION_UNAVAILABLE`| Member 2 prediction service failed and fallback is disabled. | Error reported without fabricating delay data. |
| `VALIDATION_UNAVAILABLE`| Member 4 validator service unreachable and provisional fallback disabled. | Operator alerted of missing validation step. |
| `VALIDATION_ERROR` | Member 4 returned HTTP error or invalid response schema. | Error reported with diagnostic context. |
| `OPTIMIZATION_ERROR` | Solver model formulation or internal execution error. | Logged with full stack trace. |

---

## 8. Assumptions and Prototype Disclaimers

1. **Prototype Decision Support Only:** This software is a prototype research and decision-support module developed for SIH26027. It does **not** connect to live Indian Railways signaling systems, CRIS databases, or actual train interlocking hardware, and does not claim official safety certification.
2. **Synthetic Data:** When live data feeds from Member 1 are unavailable, clearly marked synthetic demo datasets are provided in `data/synthetic/`.
3. **Pluggable Integration:** Member 2 and Member 4 interfaces are implemented via strict adapter contracts with mock fallbacks for testing.
