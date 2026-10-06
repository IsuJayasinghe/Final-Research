# AI-Powered Autonomous Smart Port Management System

An undergraduate group research project dedicated to the design, optimization, and synchronization of intelligent maritime container terminal operations through machine learning, mathematical optimization, and decision-support algorithms.

---

## 📌 Project Overview

Modern container terminals operate under high throughput demands where quayside scheduling conflicts, yard congestion, internal fleet travel delays, and landside gate bottlenecks directly compound operational costs. This research project introduces an integrated, multi-agent AI-driven port management system that synchronizes container handling across the terminal lifecycle.

The system coordinates container terminal operations across **four core research components**:

```
[Quayside Operations]          [Internal Transport]          [Container Storage]          [Landside Gate]
Component 1: Berth Allocation ──> Component 2: Drayage Truck ──> Component 3: Yard Storage ──> Component 4: Gate System
```

---

## 🏛️ System Architecture & Cross-Component Integration

The system employs an integrated architecture connecting terminal telemetry, optimization services, and operational interfaces:

```
                  Operational Telemetry & External Booking Data
                                        │
                                        ▼
                       Shared Backend Services & PostgreSQL
                                        │
    ┌───────────────────────────────────┴───────────────────────────────────┐
    │                                                                       │
    ▼                                                                       ▼
Component 1: Berth Allocation                       Component 3: Yard Storage
  │ (quayside schedules & berthing windows)           │ (block destinations & pickup slots)
  │                                                   │
  └───────────────────────────────┬───────────────────┘
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

### Operational Coordination Across Components
- **Component 1 to Component 2**: Component 1 provides quayside vessel berthing schedules, vessel turnaround windows, and quay crane availability to Component 2 for coordinating quayside container discharge and loading transfers.
- **Component 3 to Component 2**: Component 3 provides designated yard block storage zones, bay/row coordinates, and retrieval schedules to Component 2 for transport route planning and truck-task dispatch.
- **Component 2 to Components 1 & 3**: Component 2 provides real-time truck location updates, task completion signals, and equipment status feedback to Component 1 (quay crane transfer progress) and Component 3 (yard intake/discharge timing).
- **Component 4 Integration**: Component 4 coordinates landside intake and dispatch appointments, validating incoming containers and managing gate throughput to align with yard and terminal capacity.

---

## 🔬 Research Components

The system is organized into four interconnected research components. Component numbering and definitions are maintained as follows:

### Component 1: Smart Dynamic Berth Allocation System
Focuses on quayside vessel scheduling and resource allocation:
- **Vessel ETA Prediction**: Predicts accurate vessel Estimated Time of Arrival (ETA) using maritime telemetry (AIS data: SOG, COG, draft, latitude, longitude) and hydro-meteorological indicators (wind speed, wave height).
- **Vessel Delay Prediction**: Identifies arrival delays caused by maritime weather disruptions, sea states, and speed variations.
- **Berth Availability Analysis**: Evaluates quayside physical limits (berth lengths, draft thresholds, bollard layouts) against incoming vessel specifications.
- **Vessel Requirement Analysis**: Matches vessel dimensional, cargo, and handling constraints with quayside resources.
- **Dynamic Berth Assignment**: Formulates berthing schedules that optimize quayside resource utilization.
- **Berth Scheduling Optimization**: Optimizes quay crane allocation and handling schedules to minimize vessel turnaround time and demurrage costs.
- **Dynamic Rescheduling & Reallocation**: Reassesses and adjusts berthing schedules when vessel arrival times drift, handling delays occur, or adverse operational conditions develop.
- **Environmental Condition Handling**: Incorporates wind speed and wave height factors into quayside scheduling decisions.

### Component 2: Intelligent Drayage Truck Optimization System
Focuses on internal horizontal transport and vehicle fleet coordination for **human-driven internal terminal trucks**:
- **Fleet Scope**: The internal truck fleet consists of human-driven prime movers and terminal tractors. Intelligent algorithms provide dispatch and routing decision support rather than autonomous vehicle driving.
- **Operational Information Utilized**:
  - Real-time truck locations and driver availability status.
  - Current truck workload and existing assignment queues.
  - Container-transfer tasks between quayside berths, container yards, and terminal gates.
  - Pickup and destination zone requirements.
  - Task priority levels and time windows.
  - Route distances and terminal zone traffic conditions.
  - Changing congestion patterns across terminal roadways.
- **Intelligent Decision Functionality**:
  - **Suitable Truck-Task Allocation**: Assigns container transfer orders to active trucks to balance workloads and maximize fleet efficiency.
  - **Route Decision Support**: Provides real-time path guidance across terminal roadways based on zone distances and congestion levels.
  - **Adaptive Reassessment**: Recalculates assignments and schedules dynamically when delays, crane holds, or unexpected terminal events occur.
  - **Fleet Utilization**: Improves truck utilization, minimizes idle waiting times, and reduces unnecessary empty travel (deadhead distance).
  - **Efficient Container Transfers**: Accelerates cycle times for transfers between quayside, yard blocks, and gates.
- **Operational Decision Cycle**:
  ```
  Operational Data ──> State Update ──> Feasibility Check ──> Truck-Task Suitability Evaluation
          │
          └──> Task Assignment ──> Route Selection ──> Driver Execution ──> Status Update ──> Reassessment
  ```
- **Driver Mobile Application**: Delivers real-time task assignments, GPS location updates, route guidance, truck/job status updates, job completion feedback, and operational notifications directly to internal truck drivers.
- **Research Contribution**: The core intelligent contribution is adaptive truck-task and route decision support; GPS, mobile interfaces, APIs, and databases serve as enabling infrastructure.

### Component 3: Smart Container Yard Allocation & Space Utilization Optimization System
Focuses on container yard space allocation, stacking efficiency, and occupancy forecasting:
- **Container Yard Allocation**: Assigns optimal storage blocks, bays, rows, and tiers to incoming and outgoing containers according to container attributes (size, weight class, type, shipping line, cargo class).
- **Dwell-Time-Related Analysis & Prediction**: Forecasts container dwell duration to optimize stacking sequences according to anticipated departure dates.
- **Yard Occupancy Prediction**: Forecasts storage block occupancy levels and utilization patterns over operational horizons.
- **Suitable Storage-Zone Selection**: Selects storage blocks that balance crane workloads and minimize congestion at yard transfer points.
- **Yard Space Utilization Optimization**: Maximizes storage capacity and spatial density across yard blocks.
- **Reshuffling Reduction**: Minimizes unproductive container moves (re-handling) during retrieval cycles.
- **Storage Requirement Compliance**: Enforces constraints regarding container dimensions, weight-stacking safety rules, hazardous material zoning, and shipping line groupings.

### Component 4: AI-Powered Gate Appointment System
Focuses on landside terminal access control, digital appointment booking, and intake/dispatch processing:
- **Digital System Workflow**:
  ```
  Digital Desktop/Mobile Data Entry ──> Validation ──> Gate Appointment / Clearance Decision Support
          │
          └──> Suitable Gate & Arrival-Time Assignment ──> Gate Processing
  ```
- **Digital Information Submission**: Enables hauliers, logistics operators, and shipping agents to submit truck, container, cargo, vehicle, and gate-related information through structured digital forms via desktop web and mobile interfaces.
- **Appointment Request Processing**: Receives and processes appointment booking requests for external container drop-offs and pickups.
- **Information Validation**: Validates submitted cargo declarations, container identifiers (ISO 6346), vehicle registrations, and driver details before terminal arrival.
- **Gate Clearance Decision Support**: Evaluates appointment requests against terminal capacity to provide decision support for gate clearance and entry approvals.
- **Gate Congestion Prediction**: Forecasts arrival volumes and gate lane utilization to prevent queue buildup.
- **Suitable Gate & Arrival-Time Assignment**: Allocates specific gate lanes and designated arrival time-windows to balance intake flow throughout the day.
- **Appointment Status Management**: Tracks reservation states from initial submission through arrival, verification, and completion.
- **Dynamic Appointment Reassignment**: Updates appointment allocations or reassigns time slots when terminal congestion or operational conditions shift.
- **Gate Processing Support**: Coordinates external truck entry with yard receiving schedules to streamline turnaround times.

---

## 💻 Technology Stack

| Domain | Technologies | Purpose |
|---|---|---|
| **Frontend Web** | React, TypeScript | Operations dashboard, administrative portals, and gate booking interfaces |
| **Driver Mobile Application** | Mobile Application | Task receipt, GPS updates, route guidance, and job status feedback for internal truck drivers |
| **Backend Services** | Python, FastAPI | High-performance asynchronous RESTful APIs, optimization engines, and service coordination |
| **Database** | PostgreSQL (PostgreSQL 18 local development) | Multi-schema relational database storing operational entities, tracking, and logs |
| **AI / Machine Learning / Optimization** | XGBoost, Scikit-learn, Google OR-Tools, LSTM, Prophet, ARIMA | Predictive models (vessel ETA prediction, yard occupancy forecasting, dwell-time analysis) and combinatorial optimization |
| **Data Processing & Analytics** | Pandas, NumPy, Matplotlib, Seaborn | Data manipulation, feature preparation, and analytics visualization |
| **Version Control** | Git, GitHub | Distributed version control and collaborative group development |

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

The repository follows an integrated GitFlow-inspired branching strategy designed for coordinated group research development:

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
- **`main`**: The primary stable branch representing verified, end-to-end integrated versions of the system. Direct commits to `main` are restricted.
- **`develop`**: The active shared integration branch. All component teams continuously integrate and verify completed features here.
- **`feature/c1-berth`**: Dedicated branch for Component 1 (Berth Allocation System).
- **`feature/c2-drayage`**: Dedicated branch for Component 2 (Drayage Truck Optimization).
- **`feature/c3-yard`**: Dedicated branch for Component 3 (Container Yard Allocation System).
- **`feature/c4-gate`**: Dedicated branch for Component 4 (Gate Appointment System).

### Collaboration Guidelines
1. **Regular Integration**: Team members develop on their respective feature branches and regularly pull from and merge into `develop`. Independent silos merged only at the end of the project are strictly avoided.
2. **Schema Uniformity**: Database schemas are centralized under `database/schema/` across all components to ensure relational integrity.
3. **Conventional Commits**: Commit messages follow standard conventions (`feat:`, `fix:`, `docs:`, `chore:`, `db:`).

---

## 🗄️ Database Architecture Quick Reference

The local PostgreSQL database is named `smart_port_management`. It organizes port data across six logical schemas:
- `common`: Shared entities (vessels, containers, transport routes).
- `berth`: Quayside berths, AIS vessel telemetry, ETA predictions, berth allocations.
- `drayage`: Internal trucks, drivers, dispatch tasks, GPS traces, assignment logs.
- `yard`: Yard zones, container allocations, occupancy metrics.
- `gate`: Gates, external truck appointments, digital submissions, clearance logs.
- `staging`: Raw imported research datasets used for ETL and preprocessing.

See [database/README.md](database/README.md) for full setup instructions, table definitions, and execution order.

---

## 🛡️ Data Governance & Repository Security

- **Confidentiality**: Raw operational and research datasets (`*.csv`, `*.xlsx`, `*.xls`) must never be committed to public GitHub repositories.
- **Staging Isolation**: Data imported into PostgreSQL staging tables is transformed and sanitized via local ETL pipelines before entering core operational schemas.
- **Secrets Protection**: Credentials, database passwords, and API keys must never be committed; environment configuration is managed via `.env.example`.

Refer to [docs/data-management.md](docs/data-management.md) for data management protocols.