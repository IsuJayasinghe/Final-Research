# AI-Powered Autonomous Smart Port Management System
## Central Git Repository Master Documentation (Checklist 1 Submission)

**Project ID**: `J26-IT-396`  
**Academic Year**: 2026/2027 (July Batch)  
**Course Code**: IT4010 — Comprehensive Design and Analysis Project (CDAP)  
**Specialization**: B.Sc. (Hons) in Information Technology  
**Supervisor**: Dr. Junius Anjana  
**Co-Supervisor**: Mr. Nelum Amarasena  
**Official GitHub Repository**: [https://github.com/IsuJayasinghe/Final-Research](https://github.com/IsuJayasinghe/Final-Research)  

---

### 👥 Project Team & Component Allocation

| Student Name | Student ID | Specialization | Research Component Title | Dedicated Git Branch |
| :--- | :--- | :--- | :--- | :--- |
| **Siriwardena D.R.S** | `IT22143440` | Information Technology | **Component 1**: Smart Dynamic Berth Allocation System | `feature/c1-berth` |
| **Ranathunga R.A.N.G** | `IT23293144` | Information Technology | **Component 2**: Intelligent Drayage Truck Optimization System | `feature/c2-drayage` |
| **Jayasinghe I.U** | `IT23334410` | Information Technology | **Component 3**: Smart Container Yard Allocation & Space Utilization System | `feature/c3-yard` |
| **Nanayakkara** | `IT23234116` | Information Technology | **Component 4**: AI-Powered Gate Appointment System | `feature/c4-gate` |

---

## 📌 1. Project Overview & Research Context

Modern container terminals face severe synchronization challenges between quayside operations, internal horizontal transport, yard stacking buffers, and landside gate appointments. A delay in any single domain compounds across the entire logistics chain, inflating vessel turnaround times and terminal congestion.

This research project introduces an **AI-Powered Multi-Agent Autonomous Smart Port Management System** designed to synchronize operations across all four functional terminal domains:

```
[Quayside Operations]          [Internal Transport]          [Container Storage]          [Landside Gate]
Component 1: Berth Allocation ──> Component 2: Drayage Truck ──> Component 3: Yard Storage ──> Component 4: Gate System
```

---

## 🏛️ 2. High-Level System Architecture

The four components communicate through centralized PostgreSQL relational schemas and RESTful microservice APIs:

```
                         Operational Telemetry & External Booking Data
                                               │
                                               ▼
                              Shared Backend Services & PostgreSQL
                                               │
           ┌───────────────────────────────────┴───────────────────────────────────┐
           │                                                                       │
           ▼                                                                       ▼
Component 1: Berth Allocation                             Component 3: Yard Storage
  │ (quayside schedules & berthing windows)                 │ (block destinations & pickup slots)
  │                                                         │
  └───────────────────────────────┬─────────────────────────┘
                                  │
                                  ▼
                    Component 2: Drayage Truck
                      │ (movement updates & completion feedback)
                      │
                      ▼
                    Component 4: Gate System
                      (pre-arrival appointments & landside processing)
                                        │
                                        ▼
                           Web & Mobile User Interfaces
```

---

## 🔬 3. Component Breakdown & Individual Scopes

### Component 1: Smart Dynamic Berth Allocation System (`IT22143440`)
- **Domain**: Quayside vessel scheduling and crane allocation.
- **Key Modules**:
  - Vessel ETA and Arrival Delay prediction based on AIS telemetry (SOG, COG, draft) and weather indicators (wind speed, wave height).
  - Physical berth constraint verification (berth length, maximum draft, bollard spacing).
  - Dynamic berth allocation and quay crane handling optimization to minimize demurrage.
- **Branch**: `feature/c1-berth`

### Component 2: Intelligent Drayage Truck Optimization System (`IT23293144`)
- **Domain**: Internal horizontal transport coordination for human-driven terminal tractors and AGVs.
- **Key Modules**:
  - **Machine Learning**: XGBoost Regressor travel time prediction pipeline ($R^2 = 0.9951$, $\text{MAE} = 5.89\text{s}$) modeling corridor congestion and terminal kinematics.
  - **Combinatorial Optimization**: Google OR-Tools Mixed-Integer Linear Programming (MILP) bipartite dispatcher optimizing truck-task assignments and minimizing deadhead travel.
  - **Driver Mobile Application**: Flutter cross-platform mobile client providing real-time mission dispatch, task lifecycle progression, and GPS telemetry streaming.
  - **FastAPI REST Backend**: 12 operational endpoints, JWT authentication, and strict driver-level data isolation.
- **Branch**: `feature/c2-drayage`

### Component 3: Smart Container Yard Allocation & Space Utilization System (`IT23334410`)
- **Domain**: Container yard space management and stacking sequence optimization.
- **Key Modules**:
  - Block, bay, row, and tier allocation matching container weight classes, dimensions, and shipping lines.
  - Dwell-time prediction and yard occupancy forecasting.
  - Re-handling (reshuffling) reduction algorithms to accelerate container retrieval.
- **Branch**: `feature/c3-yard`

### Component 4: AI-Powered Gate Appointment System (`IT23234116`)
- **Domain**: Landside terminal access control and appointment scheduling.
- **Key Modules**:
  - Digital pre-arrival appointment booking and ISO 6346 container validation.
  - Gate lane congestion forecasting and intake throughput balancing.
  - Dynamic appointment reassignment during terminal traffic surges.
- **Branch**: `feature/c4-gate`

---

## 💻 4. Technology Stack

| Layer | Technologies | Operational Scope |
| :--- | :--- | :--- |
| **Frontend Web** | React, TypeScript, TailwindCSS, Vite | Dispatcher portals, operations monitoring, administrative consoles |
| **Driver Mobile App** | Flutter (Dart SDK 3.x, Material Design 3) | Internal terminal truck driver dispatch, GPS telemetry, route guidance |
| **Backend Microservices** | Python 3.14 / 3.11, FastAPI, Uvicorn | High-throughput asynchronous REST APIs, JWT bearer auth |
| **Database** | PostgreSQL 18 (Relational schemas: `common`, `berth`, `drayage`, `yard`, `gate`, `staging`) | Multi-schema transactional data persistence and spatial entities |
| **Machine Learning** | XGBoost 3.x, Scikit-learn, Pandas, NumPy | Container travel time regression, dwell-time forecasting, ETA models |
| **Optimization Engine** | Google OR-Tools (SCIP / CBC MILP Solvers) | Combinatorial truck-task assignment, berth scheduling |
| **Testing** | Pytest, HTTPX, Flutter Test | End-to-end automated unit, service, and lifecycle verification |
| **Version Control** | Git, GitHub | Distributed version control following GitFlow feature branching |

---

## 🗂️ 5. Repository Directory Layout

```text
smart-port-management-system/
├── backend/
│   ├── common/                 # Shared database connectors and cross-cutting utilities
│   ├── berth/                  # Component 1: Berth allocation services & ETA endpoints
│   ├── drayage/                # Component 2: Drayage truck backend, ML models, & OR-Tools optimizer
│   │   ├── ml/                 # XGBoost training pipeline, inference engine, & optimizer
│   │   ├── tests/              # Automated pytest test suites (29 tests passing 100%)
│   │   ├── config.py           # Settings loader and environment configuration
│   │   ├── database.py         # SQLAlchemy engine and non-blocking connectivity checks
│   │   ├── main.py             # FastAPI app factory, CORS middleware, lifespan events
│   │   ├── router.py           # 12 production REST endpoints
│   │   ├── schemas.py          # Pydantic data contracts and lifecycle state machines
│   │   ├── security.py         # Bcrypt password hashing and JWT bearer tokens
│   │   └── service.py          # Relational queries and business logic
│   ├── yard/                   # Component 3: Yard allocation services
│   └── gate/                   # Component 4: Gate appointment & validation services
│
├── drayage_driver_app/         # Component 2: Flutter Driver Mobile Application
│   ├── lib/                    # Application source code (core, features, models, services)
│   ├── test/                   # Automated Flutter test suites (10 tests passing 100%)
│   ├── android/                # Native Android configuration (APK builds)
│   └── pubspec.yaml            # Flutter dependencies and assets declaration
│
├── database/
│   └── schema/                 # Multi-schema SQL definitions (01_create_schemas to 07_staging)
│
├── docs/
│   └── data-management.md     # Research data governance, confidentiality, and ETL protocols
│
├── frontend/                   # Shared React + TypeScript web application landing
├── ml-models/                  # Standalone ML experimental notebooks and models
├── .gitignore                  # Strict credential, dataset, and build artifact exclusions
└── README.md                   # Repository master documentation
```

---

## 🌿 6. Git Branching & Collaboration Strategy

The repository follows a standardized GitFlow collaboration model:

```
[main] ─────────────────────────────────────────────────────────────> (Stable Production Release)
  │
  └── [develop] ────────────────────────────────────────────────────> (Shared Integration Branch)
        │
        ├── [feature/c1-berth] ──────> (Component 1 development: IT22143440) ──┐
        ├── [feature/c2-drayage] ────> (Component 2 development: IT23293144) ──┤ Pull Requests &
        ├── [feature/c3-yard] ───────> (Component 3 development: IT23334410) ──┤ Integration into
        └── [feature/c4-gate] ───────> (Component 4 development: IT23234116) ──┘ develop
```

- **`main`**: Verified, production-ready release branch.
- **`develop`**: Active team integration branch where completed features are merged and verified.
- **`feature/c2-drayage`**: Component 2 dedicated development branch actively synced with `develop`.

---

## 🛡️ 7. Data Governance, Confidentiality & Compliance

- **Dataset Security**: In strict compliance with SLIIT CDAP guidelines and institutional ethics, raw operational spreadsheets (`*.csv`, `*.xlsx`) are excluded from Git version control via `.gitignore`.
- **Credential Protection**: Database passwords and JWT secrets are managed via local `.env` files; `.env.example` templates are provided.
- **Staging Isolation**: Operational telemetry is ingested through a separate `staging` PostgreSQL schema before ETL sanitization into production tables.

---

*Compiled and submitted for CDAP Checklist 1 Evaluation — October 2026.*
