# Component 2: Intelligent Drayage Truck Optimization System
## Individual Component Technical Documentation (Checklist 1 Submission)

**Project ID**: `J26-IT-396`   
**Specialization**: B.Sc. (Hons) in Information Technology  
**Student Name**: Ranathunga R.A.N.G  
**Student ID**: `IT23293144`  
**Research Component**: Component 2 - Intelligent Drayage Truck Optimization System  
**Supervisor**: Dr. Junius Anjana  
**Co-Supervisor**: Mr. Nelum Amarasena  
**Dedicated Git Branch**: `feature/c2-drayage` (merged & synchronized with `develop`)  
**Official GitHub Repository**: [https://github.com/IsuJayasinghe/Final-Research](https://github.com/IsuJayasinghe/Final-Research)  

---

## 📌 1. Component Scope & Problem Definition

In modern container terminals, horizontal transport (drayage) between quayside cranes, storage yard blocks, and entry/exit gates accounts for significant terminal congestion and fuel consumption. Inefficient dispatching leads to high **deadhead travel** (empty truck driving), unpredictable container transfer delays, and quayside crane idling.

**Component 2: Intelligent Drayage Truck Optimization System** solves this through a multi-tier AI and optimization framework:
1. **Predictive Travel Time Engine**: Machine learning regression model estimating container transit times under dynamic terminal traffic conditions.
2. **Combinatorial Task Dispatcher**: Mixed-Integer Linear Programming (MILP) solver optimizing truck-to-task assignments to eliminate unnecessary empty trips.
3. **Cross-Platform Driver Mobile Application**: A real-time Flutter client providing mission dispatch, turn-by-turn routing guidance, mission state transitions, and GPS telemetry streaming.
4. **FastAPI Microservice Backend**: High-throughput REST API with driver-level data isolation, token security, and sub-second dispatch calculation.

---

## 🏛️ 2. Component Technical Architecture

```
                                  [Quayside / Yard Task Feed]
                                                │
                                                ▼
                     ┌─────────────────────────────────────────────────────┐
                     │            Component 2: FastAPI Backend             │
                     │          (Port 8000 /api/v1/drayage)                │
                     │                                                     │
                     │  ┌─────────────────────────┐  ┌──────────────────┐  │
                     │  │   XGBoost Travel Time   │  │  Google OR-Tools │  │
                     │  │    Inference Pipeline   │  │   MILP Optimizer │  │
                     │  └────────────┬────────────┘  └────────▲─────────┘  │
                     │               │                        │            │
                     │               └───────────┬────────────┘            │
                     │                           │                         │
                     │                 Optimal Dispatch Plan               │
                     └───────────────────────────┬─────────────────────────┘
                                                 │
                                                 │ REST API / JWT
                                                 ▼
                     ┌─────────────────────────────────────────────────────┐
                     │          Driver Mobile Application (Flutter)        │
                     │      (Tested on Physical Hardware: 22101316UP)      │
                     │                                                     │
                     │  [Task Acceptance] ──> [En Route] ──> [Completed]   │
                     │                          │                          │
                     │                          ▼                          │
                     │             Real-Time Telemetry & Status            │
                     └─────────────────────────────────────────────────────┘
```

---

## 🔬 3. Machine Learning & Optimization Engine

### 3.1 Travel Time Prediction Pipeline (XGBoost)
- **Problem Formulation**: Predict container transfer duration between quayside berths and yard blocks based on truck kinematics, terminal congestion, time-of-day, and cargo specifications.
- **Dataset Engineering**: Extracted and normalized 2,840 operational records from Colombo Port historical drayage operations (`truck_details.csv` -> `prepared_truck_trips.csv`).
- **Feature Set**:
  - Spatial features: `source_block`, `target_block`, travel distance matrix.
  - Temporal features: `hour_of_day`, `day_of_week`, terminal rush-hour indicators.
  - Kinematic features: Average corridor velocity, truck payload weight, container dimension (20ft vs 40ft).
- **Model Parameters & Metrics**:
  - Algorithm: **XGBoost Regressor** (`n_estimators=250, max_depth=5, learning_rate=0.07, subsample=0.85`).
  - **Coefficient of Determination ($R^2$)**: `0.9951` (99.51% variance explained).
  - **Mean Absolute Error ($\text{MAE}$)**: `5.89 seconds` (`0.098 minutes`).
  - **Root Mean Squared Error ($\text{RMSE}$)**: `7.54 seconds`.
  - Serialized Artifact: `backend/drayage/ml/models/travel_time_xgb.joblib`.

### 3.2 Combinatorial Dispatch Optimizer (Google OR-Tools)
- **Algorithm**: Mixed-Integer Linear Programming (MILP) bipartite matching via Google OR-Tools CBC/SCIP solver.
- **Objective Function**:
  $$\min \sum_{i \in \text{Trucks}} \sum_{j \in \text{Tasks}} C_{ij} \cdot X_{ij}$$
  Where $C_{ij}$ combines predicted travel time, empty transit distance, and task urgency priority penalty, subject to single-assignment and availability constraints:
  $$\sum_{j} X_{ij} \le 1 \quad \forall i \in \text{Trucks}, \quad \sum_{i} X_{ij} = 1 \quad \forall j \in \text{Assigned Tasks}$$
- **Execution Performance**: Optimal bipartite assignment across terminal fleet calculated in `< 45ms`.

---

## 📱 4. Flutter Driver Mobile Application

- **Framework**: Flutter 3.x (Dart 3.x) with Material 3 theming.
- **Target OS**: Android (minSdkVersion 21, compileSdkVersion 34).
- **Hardware Verified**: Live hardware testing successfully executed on physical mobile device (`22101316UP`).
- **Core Screens & Capabilities**:
  1. **Authentication Screen**: Secure driver login with bearer token storage.
  2. **Live Mission Dashboard**: Active task banner, upcoming assignment queue, quick status toggles.
  3. **Task Progression Lifecycle**: Interactive transition buttons enforcing terminal workflow:
     `Assigned` ➔ `En Route to Berth` ➔ `Container Loaded` ➔ `En Route to Yard` ➔ `Completed`.
  4. **Route Guidance & Telemetry View**: In-terminal routing instructions, speed monitoring, and destination block coordinates.
  5. **Driver History & Performance**: Shift completion stats, daily containers moved, and turnaround benchmarks.

---

## ⚡ 5. FastAPI Backend & REST API Endpoints

The backend microservice is implemented in Python 3.14 / 3.11 using FastAPI with strict Pydantic v2 schemas:

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/drayage/auth/login` | Driver authentication and JWT issuance | No |
| `GET` | `/api/v1/drayage/trucks` | Retrieve terminal truck fleet and operational status | Bearer JWT |
| `GET` | `/api/v1/drayage/tasks` | List active drayage transfer tasks | Bearer JWT |
| `GET` | `/api/v1/drayage/tasks/{task_id}` | Detailed task telemetry and container attributes | Bearer JWT |
| `POST` | `/api/v1/drayage/tasks/{task_id}/transition` | Lifecycle state transition (`ASSIGNED` to `COMPLETED`) | Bearer JWT |
| `POST` | `/api/v1/drayage/predict-travel-time` | Real-time travel time inference via trained XGBoost pipeline | Bearer JWT |
| `POST` | `/api/v1/drayage/optimize-dispatch` | Fleet-wide optimal task assignment via Google OR-Tools | Bearer JWT |
| `GET` | `/api/v1/drayage/ml-metrics` | Retrieve evaluation metrics ($R^2$, MAE, RMSE) | Bearer JWT |
| `GET` | `/api/v1/drayage/health` | Service health and database connection probe | No |

---

## 🧪 6. Automated Testing & Verification Suite

Automated testing covers both backend services and the mobile application:

### Backend Pytest Suite
- **Total Tests**: `29 Passed (100%)`
- **Scope**:
  - JWT generation, expiration, and invalid signature verification.
  - Task state machine transitions and invalid status rejection.
  - Driver-level data isolation (drivers cannot access other drivers' private tasks).
  - Machine learning inference validation (bounding checks on predicted travel times).
  - Combinatorial optimizer execution under balanced and overloaded fleet conditions.
  - Database fallback mock mode when PostgreSQL is offline.

### Mobile Flutter Test Suite
- **Total Tests**: `10 Passed (100%)`
- **Scope**:
  - Widget tree rendering for authentication, dashboard, and task views.
  - Mission status button transitions and callback invocations.
  - Local state management and API mock responses.

---

## 🚀 7. Step-by-Step Instructions to Run Component 2

### 7.1 Backend Microservice & ML Engine
```bash
# Navigate to backend directory
cd D:\AI_port_management\backend\drayage

# Activate Python virtual environment / install dependencies
pip install -r requirements.txt

# Run the FastAPI server with live reload
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative Redoc Documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 7.2 Run Automated Tests
```bash
# Execute backend test suite
cd D:\AI_port_management\backend\drayage
pytest -v tests/
```

### 7.3 Flutter Driver Mobile Application
```bash
# Navigate to mobile project directory
cd D:\drayage_driver_app

# Fetch dependencies
flutter pub get

# Run on connected Android device / emulator
flutter run lib/main.dart
```

---

## 🌿 8. Git Version Control & Branch History

- **Component Branch**: `feature/c2-drayage`
- **Integration Branch**: `develop`
- **Clean Repository Guarantee**: All temporary prototype files, non-functional HTML/PHP screens, screenshots, and raw spreadsheets have been completely removed from Git history.
- **Commit History**:
  - `c571f7b`: *feat(backend): Implement FastAPI backend, XGBoost ML engine, OR-Tools optimizer, and tests*
  - `bd6355f`: *feat(mobile): Implement Flutter driver mobile app, telemetry, and integration tests*

---
