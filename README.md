# AI-Powered Autonomous Smart Port Management System

An undergraduate group research project dedicated to the design, optimization, and automation of intelligent maritime container terminal operations through machine learning, operational research, and decision-support algorithms.

---

## 📌 Project Overview

Modern container ports face escalating congestion, scheduling conflicts, and operational bottlenecks across quayside, internal transport, yard storage, and landside gate interfaces. This research project introduces an integrated, multi-agent AI-driven port management framework designed to streamline and synchronize container handling across the terminal lifecycle.

The project models the container terminal ecosystem across **four core research components**, executed in coordinated tandem:

```
[Quayside Operations]          [Internal Transport]          [Container Storage]          [Landside Gate]
Component 1: Berth Allocation ──> Component 2: Drayage Truck ──> Component 3: Yard Storage ──> Component 4: Gate System
```

---

## 🏛️ System Architecture & Research Components

The system is organized into four interconnected research components. Component numbering and definitions are strictly maintained as follows:

### 1. Smart Dynamic Berth Allocation System (Component 1)
Focuses on quayside vessel scheduling and resource allocation:
- **Vessel ETA Prediction**: Predicts accurate vessel Estimated Time of Arrival (ETA) using maritime telemetry (AIS data: SOG, COG, draft, latitude, longitude) and hydro-meteorological indicators (wind speed, wave height).
- **Dynamic Berth Allocation**: Formulates optimal berthing schedules considering berth physical limits (draft, length, bollard spacing), crane handling capacities, and expected operational turnaround times to minimize demurrage and waiting times.

### 2. Intelligent Drayage Truck Optimization System (Component 2)
Focuses on internal horizontal transport and vehicle fleet coordination:
- **Human-Driven Internal Terminal Truck Operations**: Coordinates human-operated terminal tractors and trucks transporting containers between the berth, container yard, and gate.
- **Truck and Task Allocation**: Optimizes assignment of dispatch orders to active trucks to reduce deadhead (empty travel distance) and minimize idle waiting periods.
- **Route Decision Support**: Provides real-time path planning and dispatching guidance based on terminal zone congestion and route distances.
- **Operational-State-Aware Adaptive Reassessment**: Dynamically recalculates task assignments and priorities when delays, crane holds, or unexpected terminal events occur.
- **Driver Mobile Application Support**: Delivers dispatch assignments, turn-by-turn guidance, and status feedback to internal truck drivers via a dedicated mobile interface.

### 3. Smart Container Yard Allocation & Space Utilization Optimization System (Component 3)
Focuses on container yard space allocation and stacking efficiency:
- **Container Yard Allocation**: Assigns optimal storage blocks, bays, rows, and tiers to incoming and outgoing containers according to container attributes (size, weight class, type, shipping line, hazard class).
- **Yard Occupancy Prediction**: Forecasts yard block occupancy levels and utilization patterns over operational horizons.
- **Storage-Zone & Space-Utilization Optimization**: Minimizes container re-handling ("unproductive reshuffling") and balances crane workload across yard blocks.

### 4. AI-Powered Gate Appointment System (Component 4)
Focuses on landside terminal access control, external drayage scheduling, and intake processing:
- **Digital Data Submission Interfaces**: Enables external freight hauliers, logistics operators, and shipping agents to submit container intake/dispatch data electronically through desktop web and mobile interfaces.
- **Automated Validation**: Verifies cargo declarations, container identifiers, vehicle registrations, and driver clearance prior to terminal arrival.
- **Clearance & Appointment Decision Support**: Analyzes incoming gate appointment requests against projected yard and berth workloads to smooth peak arrival surges and assign clearance slots.
- **Gate Processing & Access Control**: Optimizes physical gate lane assignments and accelerates gate turnaround times.

> [!IMPORTANT]
> **Data Governance Notice for Component 4**:
> Component 4 is **not** primarily designed as a paper-document OCR or physical paper-scanning solution. It is built as a digital pre-clearance and appointment orchestration system. Historical digital operational data for Component 4 are currently unavailable because previous terminal gate operations were conducted manually on paper and had not been digitized at the time of research data acquisition. In accordance with academic research integrity standards, no artificial or fake historical operational datasets are fabricated for Component 4.

---

## 💻 Technology Stack

| Tier | Technologies | Purpose |
|---|---|---|
| **Frontend Web** | React, TypeScript, Tailwind CSS, Vite | Web-based operations dashboard, management portal, and gate booking interface |
| **Driver Mobile App** | Flutter / React Native | Mobile application for internal terminal truck drivers (task receipt, GPS updates, status logs) |
| **Backend Services** | Python 3.11+, FastAPI, Pydantic, SQLAlchemy | High-performance asynchronous RESTful APIs and scheduling services |
| **Database** | PostgreSQL (PostgreSQL 18 local development) | Multi-schema relational database storing operational, tracking, and transactional entities |
| **ML & Decision Models** | Python, Scikit-learn, XGBoost / LightGBM, SciPy / PuLP | Predictive models (ETA prediction, yard occupancy) and optimization algorithms |
| **Version Control** | Git, GitHub | Distributed version control and collaborative group workflow |

*Note: Initial development is configured for local PostgreSQL 18. Cloud containerization (Docker) and deployment pipelines can be integrated in later phases.*

---

## 🗂️ Project Directory Structure

```text
smart-port-management-system/
├── backend/
│   ├── common/         # Shared backend utilities, DB connectors, core models
│   ├── berth/          # Component 1: Berth allocation services & ETA endpoints
│   ├── drayage/        # Component 2: Drayage truck dispatch & tracking services
│   ├── yard/           # Component 3: Yard allocation & occupancy forecasting
│   └── gate/           # Component 4: Gate appointment & validation services
│
├── frontend/           # React + TypeScript web application
│
├── database/
│   ├── README.md       # Database architecture, schemas, and setup instructions
│   ├── schema/         # PostgreSQL schema definition SQL scripts (01 to 07)
│   ├── migrations/     # Database migration scripts
│   └── seed/           # Seed data scripts
│
├── ml-models/          # Python ML models, feature engineering, and inference pipelines
│
├── docs/
│   └── data-management.md # Data governance, ETL protocols, and confidentiality rules
│
├── .gitignore          # Repository gitignore configuration
└── README.md           # Project documentation and developer guide
```

---

## 🌿 Git Branching & Collaboration Strategy

This project follows an integrated GitFlow-inspired branching strategy designed for coordinated group research development:

```
[main] ─────────────────────────────────────────────────────────────> (Stable Production / Release)
  │
  └── [develop] ────────────────────────────────────────────────────> (Shared Integration)
        │
        ├── [feature/c1-berth] ──────> (Component 1 development) ──┐
        ├── [feature/c2-drayage] ────> (Component 2 development) ──┤ Regular pull requests
        ├── [feature/c3-yard] ───────> (Component 3 development) ──┤ and integration into develop
        └── [feature/c4-gate] ───────> (Component 4 development) ──┘
```

### Branch Definitions
- **`main`**: The primary stable branch representing thoroughly verified, end-to-end integrated versions of the system. Direct commits to `main` are restricted.
- **`develop`**: The active shared integration branch. All component teams continuously integrate and verify completed features here.
- **`feature/c1-berth`**: Dedicated branch for Component 1 (Berth Allocation System).
- **`feature/c2-drayage`**: Dedicated branch for Component 2 (Drayage Truck Optimization).
- **`feature/c3-yard`**: Dedicated branch for Component 3 (Container Yard Allocation System).
- **`feature/c4-gate`**: Dedicated branch for Component 4 (Gate Appointment System).

### Collaboration Guidelines
1. **Regular Integration**: Team members must regularly pull the latest changes from `develop` into their feature branches and submit Pull Requests back into `develop`. **Do not build four completely isolated silos and attempt a monolithic merge at the end of the project.**
2. **Schema Uniformity**: Database schemas are centralized under `database/schema/` across all components to ensure relational integrity.
3. **Commit Messages**: Write meaningful, conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `db:`).

---

## 🗄️ Database Quick Reference

The local PostgreSQL database is named `smart_port_management`. It organizes port data across six logical schemas:
- `common`: Shared entities (vessels, containers, transport routes).
- `berth`: Quayside berths, AIS vessel telemetry, ETA predictions, berth allocations.
- `drayage`: Internal trucks, drivers, dispatch tasks, GPS traces, assignment logs.
- `yard`: Yard zones/blocks, container allocations, occupancy metrics.
- `gate`: Gates, external truck appointments, digital submissions, clearance logs.
- `staging`: Raw imported research datasets used for ETL and preprocessing.

See [`database/README.md`](file:///D:/AI_port_management/database/README.md) for full setup instructions and schema details.

---

## 🛡️ Data Governance & Confidentiality

- **Confidentiality**: Raw operational and research datasets (`*.csv`, `*.xlsx`, `*.xls`) must **never** be committed to public GitHub repositories.
- **Staging Isolation**: Data imported into PostgreSQL staging tables is transformed and sanitized via ETL pipelines before entering core operational schemas.
- **No Secrets**: Never commit `.env` files, API keys, or database credentials.

Refer to [`docs/data-management.md`](file:///D:/AI_port_management/docs/data-management.md) for data management protocols.