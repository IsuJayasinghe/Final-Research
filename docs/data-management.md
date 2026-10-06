# Data Management & Governance Protocol

## 1. Overview and Purpose

This document outlines the data governance, protection, and extract-transform-load (ETL) guidelines for the **AI-Powered Autonomous Smart Port Management System** research project. Because port operations involve sensitive commercial logistics, vessel schedules, and driver telemetry, all team members must adhere to the data protocols detailed below.

---

## 2. Core Data Governance Principles

### Principle 1: Raw Research Data Stays Outside Public Git
- Under no circumstances should raw research datasets (`*.csv`, `*.xlsx`, `*.xls`, `*.parquet`, etc.) be committed to this Git repository or pushed to remote GitHub origins.
- The root `.gitignore` is pre-configured to automatically exclude CSV and Excel spreadsheets.
- Team members must maintain raw data backups securely on approved local workstations or authorized academic research cloud storage (e.g., SLIIT institutional storage).

### Principle 2: Staging Schema for Ingestion and Preprocessing
- Raw data imported from field logs or partner archives must be ingested directly into the `staging` PostgreSQL schema:
  - `staging.truck_details` (~2,840 records)
  - `staging.container_yard_data` (~2,000 records)
  - `staging.berth_characteristics` (~49 records)
  - `staging.vessel_historical_data` (~1,720 records)
- These tables mirror the uncleaned source files.
- Dedicated ETL scripts will clean, validate, normalize, and populate the target operational schemas (`common`, `berth`, `drayage`, `yard`).

### Principle 3: Component 4 Digital Data Policy
- **Historical Data Limitation**: At the time of field data collection, gate intake operations were performed manually and paper-based without digital telemetry. Consequently, **no historical digital operational dataset exists for Component 4**.
- **Research Integrity Standard**: To maintain rigorous academic authenticity, **no fake or synthetic historical datasets may be presented as actual field operational data for Component 4**.
- Component 4 modeling and evaluation will focus on modern digital data submissions (via web and mobile interfaces), algorithmic rule-based validation, pre-clearance decision support, and simulated gate throughput scenarios.

### Principle 4: Explicit Labelling of Synthetic and Test Data
- If synthetic datasets, Monte Carlo simulations, or test fixtures are generated to validate optimization algorithms or stress-test system capacity:
  - They must be explicitly labelled with the prefix `synthetic_` or `mock_`.
  - Documentation and academic publications must clearly delineate synthetic data from real empirical telemetry.

### Principle 5: Strict Secrets and Credentials Protection
- Credentials, database passwords, API tokens, and private network addresses must never be hardcoded or committed to Git.
- Use `.env.example` as a template for environment configuration.
- Local configuration files (`.env`, `.env.local`, `.env.development`) are excluded by `.gitignore`.

---

## 3. Local Dataset Summary

The local development PostgreSQL instance (`smart_port_management`, PostgreSQL 18) holds the following baseline empirical datasets within the `staging` schema:

| Table | Approximate Record Count | Domain / Description |
|---|---|---|
| `staging.truck_details` | ~2,840 rows | Internal terminal tractor jobs, zones, and distance logs |
| `staging.container_yard_data` | ~2,000 rows | Container gate-in timestamps, dimensions, and yard zone destinations |
| `staging.berth_characteristics` | 49 rows | Terminal berth lengths, draft limits, crane counts, and crane rates |
| `staging.vessel_historical_data` | ~1,720 rows | Vessel AIS trajectory points, SOG, COG, weather conditions, remaining hours |
| Component 4 Gate Historical | *0 rows (Manual paper legacy)* | No historical digital records; operations digitized via new system interfaces |

---

## 4. ETL & Data Pipeline Workflow

```
[Local Raw CSV/Excel] ──> [COPY / Ingestion Script] ──> [staging.* Tables]
                                                                │
                                                        [Data Cleaning & Validation]
                                                        [Deduplication & Formatting]
                                                                │
                                                                ▼
                                                    [common.* Dimension Tables]
                                                    [berth.* Domain Tables]
                                                    [drayage.* Domain Tables]
                                                    [yard.* Domain Tables]
```

1. **Extraction**: Raw files are ingested into PostgreSQL `staging.*` tables using local ETL scripts without polluting version control.
2. **Transformation**: Normalization of container IDs, timestamp timezone conversions (UTC / local port time), validation of vessel identifiers (IMO/MMSI), and outlier removal.
3. **Loading**: Population of dimension tables (`common.vessels`, `common.containers`, `common.routes`) followed by transactional and tracking tables.
