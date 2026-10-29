# Component 4: AI-Powered Gate Appointment & Congestion Management System
## Individual Component Technical Documentation (Checklist 1 Submission)

**Project ID**: `J26-IT-396`  
**Specialization**: B.Sc. (Hons) in Information Technology  
**Student Name**: Nanayakkara T.  
**Student ID**: `IT23234116`  
**Research Component**: Component 4 — AI-Powered Gate Appointment System  
**Supervisor**: Dr. Junius Anjana  
**Co-Supervisor**: Mr. Nelum Amarasena  
**Dedicated Git Branch**: `feature/c4-gate`  
**Official GitHub Repository**: [https://github.com/IsuJayasinghe/Final-Research](https://github.com/IsuJayasinghe/Final-Research)  

---

## 📌 1. Component Scope & Problem Definition

Port container terminals experience severe landside congestion caused by uncoordinated external truck arrivals, physical gate processing bottlenecks, and unpredictable truck arrival behavior. Traditional terminal Truck Appointment Systems (TAS) suffer from fundamental operational flaws:
1. **Capacity Loss Due to No-Shows**: Static TAS systems reject booking requests once a nominal slot capacity is reached. However, empirical terminal data reveals an observed **8.4% no-show rate** and **22.2% late arrival rate**, leaving critical gate and yard crane capacity unutilized.
2. **Congestion Penalties from Blind Overbooking**: Naive overbooking (+20% static allowance) creates severe queue surges during peak hours, inflating 90th-percentile (p90) truck wait times from 5.8 minutes to **11.1 minutes**.
3. **Manual Paperwork Chokeholds**: Physical document inspection at gate kiosks (CUSDEC, VGM certificates, gate passes, driver licenses) creates severe clearance delays (exceeding 20 minutes for high-scrutiny cargo) and gate lane blockage.

**Component 4: AI-Powered Gate Appointment System** resolves these bottlenecks through an integrated machine learning, mathematical optimization, and pre-arrival digital OCR verification framework:
* **Predictive Congestion Forecasting**: 24-hour per-lane queue and waiting time forecasting using seasonal time-series models.
* **Calibrated Probabilistic No-Show Engine**: Machine learning model estimating individual booking arrival probabilities with SHAP explainability.
* **Stochastic Expected-Arrivals Overbooking**: Dynamic slot allocation allowing bookings beyond nominal capacity while strictly bounding expected physical arrivals.
* **Automated Pre-Arrival Document OCR**: In-memory computer vision pipeline extracting and cross-validating 7 shipping document types with ISO 6346 compliance.
* **Combinatorial Disruption Re-Optimizer**: Mixed-Integer Linear Programming (MILP) engine dynamically rebalancing gate lanes and appointment windows during vessel delays or lane closures.

---

## 🏛️ 2. Component Technical Architecture

```
                                External Truck Carriers / Drayage Drivers
                                                    │
                                                    ▼
                     ┌─────────────────────────────────────────────────────────────┐
                     │                 Frontend Web Portal (React 18)              │
                     │          (Driver Portal, Gate Desk, Disruption Console)     │
                     └──────────────────────────────┬──────────────────────────────┘
                                                    │ REST API
                                                    ▼
                     ┌─────────────────────────────────────────────────────────────┐
                     │              Component 4: FastAPI Microservice              │
                     │                 (Port 8000 /api/appointments)               │
                     │                                                             │
                     │  ┌─────────────────────────┐   ┌─────────────────────────┐  │
                     │  │    RapidOCR Document    │   │     SARIMAX Per-Lane    │  │
                     │  │   Verification Engine   │   │   Congestion Forecaster │  │
                     │  └────────────┬────────────┘   └────────────┬────────────┘  │
                     │               │                             │               │
                     │               ▼                             ▼               │
                     │  ┌─────────────────────────┐   ┌─────────────────────────┐  │
                     │  │   XGBoost Clearance     │   │   Calibrated XGBoost    │  │
                     │  │     Time Regressor      │   │   No-Show Risk Engine   │  │
                     │  └────────────┬────────────┘   └────────────┬────────────┘  │
                     │               │                             │               │
                     │               └──────────────┬──────────────┘               │
                     │                              ▼                              │
                     │               ┌─────────────────────────────┐               │
                     │               │ Stochastic Expected-Arrival │               │
                     │               │   & PuLP/CBC MILP Engine    │               │
                     │               └──────────────┬──────────────┘               │
                     └──────────────────────────────┼──────────────────────────────┘
                                                    │
                                                    ▼
                     ┌─────────────────────────────────────────────────────────────┐
                     │              Storage & Persistence Layer                    │
                     │    (In-Memory Mock Repository / PostgreSQL `gate` Schema)   │
                     └─────────────────────────────────────────────────────────────┘
```

---

## 🔬 3. Machine Learning & Predictive Engines

Component 4 integrates three specialized machine learning models and an end-to-end framework evaluation:

### 3.1 Model 1: Per-Lane Congestion & Queue Forecasting (SARIMAX)
- **Objective**: Forecast hourly truck queue lengths and waiting times across 6 distinct terminal entry lanes (`GATE-1` to `GATE-6`).
- **Formulation**: Seasonal Autoregressive Integrated Moving Average with eXogenous regressors (SARIMAX) capturing 24-hour daily periodicity and terminal work shifts.
- **Performance**:
  - Outperforms naive lag baselines across all 6 terminal gates.
  - Distinguishes between operational states: *Normal* (<4 trucks queued), *Busy* (4–7 trucks), and *Congested* (8+ trucks).
  - Compact precomputed inferences exported to `backend/gate/data/congestion_forecast.json` for sub-millisecond API response times.

### 3.2 Model 2: Calibrated No-Show & Late Arrival Risk Engine (XGBoost)
- **Objective**: Estimate multinomial arrival probabilities for each booking:
  $$P(\text{on\_time}), \quad P(\text{late}), \quad P(\text{no\_show})$$
- **Dataset & Features**:
  - 14,000 operational booking records partitioned into 11,200 training and 2,800 testing rows (strict chronological 80/20 holdout).
  - Features include: Carrier historical reliability score, booking lead time, booked arrival hour, ambient weather conditions, terminal traffic index, vessel delay status, customs risk category, and missing document count.
- **Model Training & Calibration**:
  - Evaluated Logistic Regression vs. XGBoost Classifier.
  - Selected model: **XGBoost Classifier**.
  - Trained **without artificial class weights** to preserve raw probability calibration for the mathematical overbooking layer.
  - **Calibration Benchmark**: Mean predicted no-show rate = `8.03%` vs. Observed test no-show rate = `8.39%` (Brier score: `0.0711`).
  - **Discrimination**: No-show ROC-AUC = `0.741`; Precision-Recall AUC = `0.249` (2.96x improvement over the 8.4% random baseline).
- **Explainability**: SHAP (SHapley Additive exPlanations) values compute the primary risk drivers for each booking (e.g., missing pre-clearance documents, low carrier reliability, extreme booking lead time).

### 3.3 Model 3: Dynamic Gate Clearance Duration Prediction (XGBoost)
- **Objective**: Predict physical booth transaction and inspection duration (minutes) for incoming trucks.
- **Model Comparison & Performance**:
  - Baseline Mean Predictor: $\text{RMSE} = 11.15 \text{ min}$, $\text{MAE} = 8.65 \text{ min}$, $\text{MAPE} = 66.02\%$.
  - Random Forest Regressor: $\text{RMSE} = 3.03 \text{ min}$, $\text{MAE} = 2.43 \text{ min}$.
  - **Trained XGBoost Regressor**: **$\text{RMSE} = 3.005 \text{ min}$** (73% error reduction), **$\text{MAE} = 2.415 \text{ min}$**, **$\text{MAPE} = 19.31\%$**.
  - Serialized Artifact: `backend/gate/models/clearance_time_model.joblib`.

### 3.4 60-Day Terminal Simulation & Policy Evaluation
A comprehensive 60-day discrete-event simulation was conducted across 6 gate lanes (300 booking requests/day sampled from held-out operational data) comparing three operational policies:

| Operational Policy | Trucks Served / Day | Rejected Requests / Day | Avg Wait Time | 90th-Percentile (p90) Wait | Slot Adherence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Static TAS** | 266.4 | 8.27 | 1.48 min | 5.78 min | 88.9% |
| **Blind +20% Overbooking** | 273.9 (+2.8%) | 0.10 | 3.12 min (+110%) | 11.10 min (+92%) | 88.9% |
| **Component 4 AI Framework** | **271.8 (+2.0%)** | **2.42** | **1.86 min (+0.38 min)** | **7.27 min** | **88.9%** |

#### Capacity Sensitivity Analysis:
Under scarce capacity scenarios (e.g., slot capacity = 12), the AI framework recovers **+9.8 served trucks per day (+4.2%)** while adding only 0.10 minutes to average wait times, completely avoiding the severe 3.0+ minute wait spikes induced by blind overbooking.

---

## ⚙️ 4. Mathematical Optimization & Automated OCR Pipeline

### 4.1 Expected-Arrivals Overbooking Rule (`scheduler.py`)
Rather than relying on static capacity thresholds, slot admittance is governed by the sum of individual arrival probabilities:
$$\mathbb{E}[\text{Arrivals}] = \sum_{b \in \text{Slot}} \left(1 - P(\text{no-show}_b)\right) \le C_{\text{nominal}}$$
A hard overbooking ceiling ($\text{Capacity} \times 1.25$) protects against unforeseen correlated arrivals.

### 4.2 Combinatorial Disruption Re-Optimizer (PuLP / CBC MILP)
When quayside vessel delays occur or unexpected gate lane closures arise:
- Confirmed appointments and trucks already arriving are **strictly frozen**.
- Unconfirmed and pending appointments are dynamically reassigned to alternative time windows and lower-congestion lanes using a Mixed-Integer Linear Program (MILP) solved via CBC.
- Every reassignment generates an auditable reason string recorded in the database event log.

### 4.3 Automated Pre-Arrival Document OCR Engine (`documents.py`)
- Powered by **RapidOCR** (ONNX runtime) executing entirely in-memory with zero local file persistence.
- Handles both digital PDF text streams and scanned imagery.
- Automatically categorizes and audits **7 essential document slots**:
  1. *Booking Confirmation*
  2. *Customs Declaration (CUSDEC)*
  3. *Gate Pass*
  4. *Verified Gross Mass (VGM) Certificate*
  5. *Container & Seal Photographic Inspection*
  6. *Driver Identification & Vehicle License*
  7. *Special Cargo Clearance (Dangerous Goods / Temperature Controlled)*
- **Data Validation Logic**:
  - ISO 6346 container number check-digit calculation with OCR character repair (`O` $\leftrightarrow$ `0`, `I` $\leftrightarrow$ `1`).
  - Weight plausibility checking ($1,000 \text{ kg} \le \text{VGM} \le 40,000 \text{ kg}$).
  - UN number validation for hazardous cargo and temperature set-point validation for refrigerated containers.
  - Automated verdict issuance: `cleared`, `flagged`, or `unreadable`.

---

## 💻 5. Microservice Backend & Frontend Implementation

### 5.1 FastAPI Backend Microservice (`backend/gate/`)
The backend exposes over 25 operational endpoints organized into distinct functional domains:

| Category | Method | Endpoint | Functional Description |
| :--- | :--- | :--- | :--- |
| **Appointments** | `POST` | `/api/appointments` | Risk evaluation, slot selection via overbooking rule, lane assignment |
| | `GET` | `/api/appointments` | Filter active appointments by truck ID or lifecycle status |
| | `GET` | `/api/appointments/{id}/events` | Full immutable audit trail of assignments and status changes |
| | `POST` | `/api/appointments/{id}/approve` | Gate admin confirms booking; unlocks pre-arrival document upload |
| | `POST` | `/api/appointments/{id}/reject` | Reject appointment with mandatory justification |
| | `POST` | `/api/appointments/{id}/cancel` | Driver cancellation prior to gate arrival |
| **Gate Desk** | `GET` | `/api/gates/{lane}/desk` | Gate officer console: real-time lane queue, document audit cards |
| | `POST` | `/api/appointments/{id}/check-in` | Physical truck arrival at gate booth (`CONFIRMED` $\to$ `ARRIVED`) |
| | `POST` | `/api/appointments/{id}/complete` | Kiosk clearance completion; records physical turnaround time |
| | `POST` | `/api/appointments/{id}/no-show` | Kiosk flag when booking window expires without arrival |
| **Driver Telemetry** | `GET` | `/api/appointments/{id}/live` | Driver live mission tracking: phase, target gate, queue, wait estimate |
| | `GET` | `/api/appointments/{id}/notifications`| Driver real-time alerts (approvals, lane changes, delays) |
| **Congestion & Lanes**| `GET` | `/api/congestion/profile` | 24-hour terminal-wide queue and waiting time forecast |
| | `GET` | `/api/lane-view` | Real-time status, wait, and active appointments for all 6 lanes |
| | `POST` | `/api/lanes/{lane}/close` | Emergency lane closure; automatically reassigns pending traffic |
| | `POST` | `/api/rebalance` | Shifts trucks from congested lanes to quieter lanes at matching hour |
| **Disruptions** | `POST` | `/api/reoptimize` | Applies vessel delay / queue surge and triggers PuLP MILP re-optimization |
| | `DELETE`| `/api/disruption` | Clears active disruption and restores baseline schedules |
| **Document OCR** | `POST` | `/api/documents/check` | In-memory RapidOCR extraction, ISO check digit, and validation |
| | `GET` | `/api/appointments/{id}/documents` | Retrieve OCR extraction verdicts and validation warnings |
| | `POST` | `/api/appointments/{id}/documents/submit`| Submit verified docs; triggers re-scoring of no-show & clearance models |
| **Analytics** | `GET` | `/api/model-metrics` | Evaluation reports for SARIMAX, XGBoost, and 60-day simulation |

### 5.2 React Web Application (`frontend/`)
A responsive React 18 + Vite frontend with TailwindCSS provides dedicated views for all terminal stakeholders:
- **`Appointments.jsx` & `GateAppointment.jsx`**: Carrier booking wizard with 24-hour congestion heatmaps.
- **`DocumentUpload.jsx`**: Interactive drag-and-drop document upload with real-time OCR extraction cards.
- **`MyTrip.jsx`**: Driver mobile-responsive live trip guidance showing gate lane, queue, and estimated entry.
- **`GateDesk.jsx` & `Approvals.jsx`**: Gate officer workstation displaying live truck queues, document verification verdicts, and check-in buttons.
- **`GateAllocationView.jsx`**: Terminal manager multi-lane dispatch overview.
- **`Optimization.jsx`**: Interactive disruption simulator injecting vessel delays and triggering MILP re-optimization.
- **`ModelResults.jsx`**: Model metrics dashboard rendering ROC-AUC curves, SHAP importances, and simulation graphs.

---

## 🧪 6. Automated Testing & Verification Suite

Component 4 maintains an extensive automated test suite executed via Pytest:

| Test Module | Coverage Scope |
| :--- | :--- |
| `test_service.py` | Appointment creation, status transitions, and service business logic |
| `test_noshow.py` | Feature vector building, XGBoost no-show inference, and SHAP calculations |
| `test_scheduler.py` | Expected-arrivals overbooking rule and capacity threshold enforcement |
| `test_documents.py` | RapidOCR parsing, ISO 6346 check digit algorithm, and field extraction |
| `test_api_documents.py` | REST API document upload, validation rejection, and 409 conflict checks |
| `test_gate_desk.py` | Gate desk officer work list, lane queues, and cross-document warnings |
| `test_gate_changes.py` | Lane closures, emergency traffic rebalancing, and disruption handling |
| `test_templates.py` | Container-specific document requirements (dry, reefer, hazardous) |
| `test_real_layouts.py` | OCR extraction against photorealistic form layouts and synthetic noise |
| `test_repository.py` | In-memory repository state isolation and transactional consistency |
| `test_weather.py` | Hydro-meteorological condition lookups and weather impact scoring |
| `test_vessels.py` | Quayside vessel delay integration and carrier lookup services |

---

## 🚀 7. Step-by-Step Instructions to Run Component 4

### 7.1 Backend Microservice & ML Models
```bash
# Navigate to gate backend directory
cd D:\AI_port_management\backend\gate

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI standalone server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative Redoc Documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 7.2 Populate Realistic Demo Data
```bash
# Seed 60 realistic appointments matching the 24-hour terminal demand curve
python tools/seed_demo_bookings.py

# Optional: Generate synthetic test documents for OCR verification
python tools/make_demo_appointments.py --book --approve
```

### 7.3 Frontend Web Portal
```bash
# Navigate to frontend directory
cd D:\AI_port_management\frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```
- Access Frontend UI: [http://localhost:5173](http://localhost:5173)

### 7.4 Execute Automated Test Suite
```bash
cd D:\AI_port_management\backend\gate
pytest -v tests/
```

---

## 🌿 8. Git Version Control & Branch History

- **Component Branch**: `feature/c4-gate`
- **Lead Developer**: Nanayakkara T. (`IT23234116`)
- **Key Contributions**:
  - Implemented SARIMAX per-lane congestion forecasting models.
  - Developed calibrated XGBoost no-show classifier with SHAP explainability.
  - Built XGBoost clearance duration regressor achieving $73\%$ RMSE reduction.
  - Implemented expected-arrivals overbooking scheduler and PuLP MILP re-optimizer.
  - Designed in-memory RapidOCR pre-arrival document verification pipeline.
  - Implemented 25+ FastAPI REST endpoints and React 18 multi-role frontend application.
  - Created 15+ automated Pytest verification test suites.

---
