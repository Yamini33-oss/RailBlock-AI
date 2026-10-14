# KAVACH BIE (Member 3) — Comprehensive Railway Data Catalog & Quality Report

> **Generated at:** 2026-10-14 05:53:15 UTC  
> **Pipeline Version:** 1.0.0  
> **Overall Quality Status:** **PASSED**  

---

## 1. Executive Summary

The KAVACH BIE Member 3 data engineering pipeline ingests, validates, and standardizes authentic, legally accessible Indian Railways operational data. The datasets span nationwide stations, scheduled train services, detailed timetable halts, and derived track block section traffic density curves.

| Dataset ID | Name | Format | Rows | Columns | File Size | Classification | Quality Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ir_stations_master` | Indian Railways Stations Master Directory | GeoJSON / JSON | 8,990 | 7 | 593.3 KB | `REAL_PUBLIC` | **PASSED** |
| `ir_trains_master` | Indian Railways Train Services Master Registry | GeoJSON / JSON | 5,208 | 13 | 526.9 KB | `REAL_PUBLIC` | **PASSED** |
| `ir_schedules_master` | Indian Railways Train Halts & Route Schedules | JSON | 417,080 | 8 | 30.61 MB | `REAL_PUBLIC` | **PASSED** |
| `ir_section_density_derived` | Trunk Corridor Section Traffic Density Indices | CSV | 192 | 8 | 15.3 KB | `DERIVED_FROM_REAL` | **PASSED** |
| `ir_corridor_track_sections` | Indian Railways Trunk Corridors & Track Block Sections | CSV | 8 | 9 | 0.6 KB | `DERIVED_FROM_REAL` | **PASSED** |

---

## 2. Detailed Dataset Profiles

### `ir_stations_master`: Indian Railways Stations Master Directory
- **Source Organization:** DataMeet Open Data Initiative / Indian Railways NTES
- **Source URL:** [https://github.com/datameet/railways](https://github.com/datameet/railways)
- **Download URL:** https://raw.githubusercontent.com/datameet/railways/master/stations.json
- **License / Terms of Use:** Open Data Commons Open Database License (ODbL) v1.0
- **Classification:** `REAL_PUBLIC`
- **Update Frequency:** Periodic / Semi-Annual
- **Description:** Complete directory of 8,990+ Indian Railway passenger and freight stations, including official station codes (e.g. NDLS, HWH, BPL), full station names, railway zones (NR, WR, NCR, etc.), state jurisdictions, and geographic coordinates.
- **Raw Download Size:** 1.778 MB (1,864,683 bytes)
- **Download Timestamp:** 2026-10-14T05:24:23.447394+00:00
- **SHA-256 Hash:** `9bd5e1da3a859e5359a95f40b6009aa468efb177da4faac57ffdcd7daeb4df18`

### `ir_trains_master`: Indian Railways Train Services Master Registry
- **Source Organization:** DataMeet Open Data Initiative / Indian Railways Public Timetable
- **Source URL:** [https://github.com/datameet/railways](https://github.com/datameet/railways)
- **Download URL:** https://raw.githubusercontent.com/datameet/railways/master/trains.json
- **License / Terms of Use:** Open Data Commons Open Database License (ODbL) v1.0
- **Classification:** `REAL_PUBLIC`
- **Update Frequency:** Periodic / Annual Timetable Revision
- **Description:** Registry of 5,200+ scheduled Indian Railway train services, including train numbers, commercial names (e.g., Rajdhani Express, Shatabdi Express, Mail/Express, DEMU), origin and terminus station codes, operating railway zones, route distances (km), scheduled departure/arrival times, and operating days.
- **Raw Download Size:** 14.084 MB (14,768,598 bytes)
- **Download Timestamp:** 2026-10-14T05:24:24.937733+00:00
- **SHA-256 Hash:** `e434d9c56016ccdf2291ccd446586ef87a7fab101084efa5f68871ab27800167`

### `ir_schedules_master`: Indian Railways Train Halts & Route Schedules
- **Source Organization:** DataMeet Open Data Initiative / National Train Enquiry System (NTES)
- **Source URL:** [https://github.com/datameet/railways](https://github.com/datameet/railways)
- **Download URL:** https://raw.githubusercontent.com/datameet/railways/master/schedules.json
- **License / Terms of Use:** Open Data Commons Open Database License (ODbL) v1.0
- **Classification:** `REAL_PUBLIC`
- **Update Frequency:** Periodic / Annual
- **Description:** Large-scale operational schedule database (~14 MB) containing intermediate station stops, scheduled arrival and departure times, day counts, and sequence indices for Indian Railway trains. Enables precise detection of train movements through any given track section.
- **Raw Download Size:** 78.368 MB (82,174,280 bytes)
- **Download Timestamp:** 2026-10-14T05:24:35.233949+00:00
- **SHA-256 Hash:** `105d63816acb177eac30a7d156eb2d312625a42ddebd273edee810d2989878ec`

### `ir_section_density_derived`: Trunk Corridor Section Traffic Density Indices
- **Source Organization:** KAVACH BIE Data Engineering Pipeline (Derived from Real Schedules)
- **Source URL:** [https://data.gov.in/ (Ministry of Railways / CRIS Schedule Synthesis)](https://data.gov.in/ (Ministry of Railways / CRIS Schedule Synthesis))
- **Download URL:** Derived internally by pipeline
- **License / Terms of Use:** Derived / Open Government Data License - India (GODL)
- **Classification:** `DERIVED_FROM_REAL`
- **Update Frequency:** Computed on Timetable Ingestion
- **Description:** Computed hourly traffic frequency and section occupancy density indices across critical trunk railway corridors (e.g. New Delhi - Mathura - Agra, Agra - Jhansi - Bhopal, Howrah - Asansol - Mughalsarai). Derived directly from 5,000+ scheduled train movements.

### `ir_corridor_track_sections`: Indian Railways Trunk Corridors & Track Block Sections
- **Source Organization:** KAVACH BIE Data Engineering Pipeline (Derived from Stations & Schedules)
- **Source URL:** [https://github.com/datameet/railways](https://github.com/datameet/railways)
- **Download URL:** Derived internally by pipeline
- **License / Terms of Use:** Derived / Open Database License (ODbL)
- **Classification:** `DERIVED_FROM_REAL`
- **Update Frequency:** Computed on Timetable Ingestion
- **Description:** Relational mapping of contiguous inter-station track block sections along major high-density routes, tracking section lengths, electrification status, and double/quadruple track indicators.

---

## 3. Data Integrity & Verification Checklist

- [x] Zero duplicate station codes in `stations_processed.csv`
- [x] Zero duplicate train numbers in `trains_processed.csv`
- [x] 100% referential integrity between schedule stops and train numbers
- [x] 100% referential integrity between schedule station codes and station master
- [x] Valid 24-hour traffic density indices ($0.0 \le \rho \le 1.0$) across trunk corridors
- [x] All raw downloads verified with SHA-256 hashes

---
*Report automatically generated by KAVACH BIE Member 3 Pipeline.*