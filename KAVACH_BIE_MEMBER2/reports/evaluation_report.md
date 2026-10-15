# KAVACH BIE — Member 2: Model Evaluation Report
**AI/ML Train Delay Prediction Module**

> **IMPORTANT DISCLAIMER**: This evaluation was executed using deterministic **synthetic railway operational data**. The metrics below demonstrate model architecture, preprocessing pipeline integrity, and relative comparative performance. They must **not** be presented as certified real-world Indian Railways accuracy.

---

## 1. Executive Summary
- **Champion Model**: `RidgeRegression`
- **Model Version**: `1.1.0`
- **Evaluation Date**: `2026-10-14T11:41:44.318915`
- **Prediction Target**: `historical_delay_minutes`
- **Test Sample Size**: `420` records (chronological split)

| Evaluation Metric | Model Score | Baseline Score (Median) | Improvement | Railway Operations Interpretation |
|:---|:---:|:---:|:---:|:---|
| **MAE (Mean Absolute Error)** | **10.87 mins** | 12.52 mins | **+13.2%** | On average, predictions deviate by 10.9 minutes from scheduled section delay. |
| **RMSE (Root Mean Squared Error)** | **16.48 mins** | 18.99 mins | **+13.2%** | Penalizes large delay outliers (e.g. major cascading congestion). |
| **R² (Coefficient of Determination)** | **0.2001** | 0.0000 | N/A | Proportional variance in historical delay explained by corridor features. |

---

## 2. Multi-Model Benchmark Comparison
All candidate models were trained on identical training splits and evaluated on the hold-out chronological test set.

| Model Candidate | Test MAE (mins) | Test RMSE (mins) | Test R² | Status |
|:---|:---:|:---:|:---:|:---:|
| `DummyBaseline` | 12.63 | 19.60 | -0.1306 | Evaluated |
| `RidgeRegression` | 10.87 | 16.48 | 0.2001 | 🏆 **Selected Champion** |
| `RandomForest` | 11.58 | 17.30 | 0.1193 | Evaluated |
| `GradientBoosting` | 11.45 | 17.60 | 0.0884 | Evaluated |

---

## 3. Residual Error Distribution
Analyzing the spread of prediction errors ($y_{actual} - \hat{y}_{predicted}$) ensures predictions do not suffer from systemic bias:

- **Mean Error (Bias)**: `1.30` minutes
- **Median Absolute Error**: `7.34` minutes
- **25th Percentile Error**: `-7.80` minutes
- **75th Percentile Error**: `6.79` minutes
- **95th Percentile Error**: `29.60` minutes (95% of test predictions are within this error bound)
- **Max Absolute Error**: `105.16` minutes

---

## 4. Sliced Error Analysis
To ensure reliable operation across varying operational contexts, model performance is evaluated across operational slices:

### A. Performance by Corridor Traffic Density
| Traffic Level | Test Samples | MAE (mins) | RMSE (mins) | Operational Note |
|:---|:---:|:---:|:---:|:---|
| `HIGH (>0.85)` | 153 | **15.89** | 22.12 | Error profile under heavy congestion |
| `LOW (<0.60)` | 179 | **6.29** | 8.12 | Error profile under standard operations |
| `MEDIUM (0.60-0.85)` | 88 | **11.44** | 17.66 | Error profile under standard operations |

### B. Performance by Track Section Corridor
| Track Section | Test Samples | MAE (mins) | RMSE (mins) |
|:---|:---:|:---:|:---:|
| `SEC_BCT_ST` | 84 | **13.16** | 20.66 |
| `SEC_CNB_PRYJ` | 60 | **7.35** | 10.96 |
| `SEC_GKP_BST` | 60 | **6.98** | 8.62 |
| `SEC_HWH_ASN` | 72 | **9.86** | 13.31 |
| `SEC_NDLS_CNB` | 84 | **15.29** | 20.84 |
| `SEC_SBC_MAS` | 60 | **10.08** | 17.01 |

### C. Performance by Operational Time Period
| Time Period | Test Samples | MAE (mins) | RMSE (mins) |
|:---|:---:|:---:|:---:|
| `AFTERNOON` | 72 | **8.65** | 12.20 |
| `LATE_NIGHT` | 36 | **7.98** | 10.14 |
| `NIGHT` | 96 | **4.83** | 6.52 |
| `PEAK_EVENING` | 84 | **13.87** | 20.52 |
| `PEAK_MORNING` | 132 | **15.34** | 21.36 |

---

## 5. Top Feature Influences
Relative importance of primary corridor and operational variables:

| Feature Name | Relative Importance Score | Operational Significance |
|:---|:---:|:---|
| `track_section_SEC_NDLS_CNB` | 0.1353 | Statistical correlation with section delay dynamics |
| `time_period_LATE_NIGHT` | 0.0956 | Statistical correlation with section delay dynamics |
| `traffic_density` | 0.0877 | Statistical correlation with section delay dynamics |
| `time_period_NIGHT` | 0.0851 | Statistical correlation with section delay dynamics |
| `track_section_SEC_CNB_PRYJ` | 0.0713 | Statistical correlation with section delay dynamics |
| `track_utilization` | 0.0691 | Statistical correlation with section delay dynamics |
| `hour_of_day` | 0.0634 | Statistical correlation with section delay dynamics |
| `time_period_AFTERNOON` | 0.0606 | Statistical correlation with section delay dynamics |
| `time_period_PEAK_MORNING` | 0.0565 | Statistical correlation with section delay dynamics |
| `track_section_SEC_SBC_MAS` | 0.0486 | Statistical correlation with section delay dynamics |

---

## 6. Metric Definitions for Railway Operations
1. **MAE (Mean Absolute Error)**: Average absolute magnitude of error. Useful for maintenance planners to gauge typical expected margin of error on timetables.
2. **RMSE (Root Mean Squared Error)**: Emphasizes larger errors heavily through squaring. Crucial for detecting whether severe delays are significantly underestimated.
3. **R² Score**: Quantifies the percentage of variation in corridor delay accounted for by schedule times, density, and corridor history.
