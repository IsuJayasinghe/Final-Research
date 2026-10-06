# Data Management & Governance Protocol

## 1. Overview and Purpose

This document outlines the data governance, security, and extract-transform-load (ETL) guidelines for the **AI-Powered Autonomous Smart Port Management System** research project. Because terminal operations involve sensitive logistics schedules, vehicle telemetry, and commercial cargo declarations, all project contributors must follow the data management protocols detailed below.

---

## 2. Core Data Governance Protocols

### Data Confidentiality and Repository Security
- Raw operational datasets (`*.csv`, `*.xlsx`, `*.xls`, `*.parquet`, etc.) must not be committed to this Git repository or pushed to public remote branches.
- The root `.gitignore` is configured to exclude data spreadsheets and raw files.
- Team members must maintain raw dataset copies securely on local development machines or authorized institutional storage.

### Staging Schema for Ingestion and Preprocessing
- Raw data imported from operational logs are ingested directly into the dedicated PostgreSQL `staging` schema:
  - `staging.truck_details` (~2,840 records)
  - `staging.container_yard_data` (~2,000 records)
  - `staging.berth_characteristics` (~49 records)
  - `staging.vessel_historical_data` (~1,720 records)
- The staging tables provide an isolated landing zone that mirrors raw source formats prior to transformation.
- Dedicated ETL scripts validate, clean, normalize, and populate target operational schemas (`common`, `berth`, `drayage`, `yard`, `gate`).

### Data Validation and Integrity
- Foreign key dependencies, uniqueness constraints, and domain checks are enforced at the database level.
- Missing values, format anomalies, and coordinate ranges must be verified during preprocessing before loading into production schemas.

### Credential Isolation and Secrets Protection
- Database credentials, API tokens, passwords, and private network addresses must never be hardcoded or committed to version control.
- Configuration templates are provided via `.env.example`.
- Local environment files (`.env`, `.env.local`, `.env.*`) are strictly excluded by `.gitignore`.

---

## 3. Staging Dataset Summary

The local development PostgreSQL instance (`smart_port_management`, PostgreSQL 18) maintains the following baseline operational datasets within the `staging` schema:

| Staging Table | Approximate Record Count | Operational Domain |
|---|---|---|
| `staging.truck_details` | ~2,840 rows | Internal terminal truck trips, zones, and distance logs |
| `staging.container_yard_data` | ~2,000 rows | Container gate-in timestamps, dimensions, and yard zone destinations |
| `staging.berth_characteristics` | 49 rows | Terminal berth lengths, draft limits, crane counts, and crane rates |
| `staging.vessel_historical_data` | ~1,720 rows | Vessel AIS trajectory points, SOG, COG, weather conditions, remaining hours |

---

## 4. ETL & Data Pipeline Workflow

```
[Local Raw Data Files] ──> [Ingestion / COPY Script] ──> [staging.* Tables]
                                                                  │
                                                          [Data Cleaning & Validation]
                                                          [Deduplication & Formatting]
                                                                  │
                                                                  ▼
                                                      [common.* Dimension Tables]
                                                      [berth.* Domain Tables]
                                                      [drayage.* Domain Tables]
                                                      [yard.* Domain Tables]
                                                      [gate.* Domain Tables]
```

1. **Extraction**: Raw records are ingested into PostgreSQL `staging.*` tables via local scripts without committing raw data to version control.
2. **Transformation**: Schema normalization, timestamp alignment (timezone harmonization), coordinate validation, identifier verification (IMO, MMSI, ISO 6346 container numbers), and outlier handling.
3. **Loading**: Structured insertion into `common` dimension tables followed by domain-specific tables across `berth`, `drayage`, `yard`, and `gate` schemas.
