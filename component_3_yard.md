# Component 3 – Smart Container Yard Allocation and Space Utilization Optimization System

**Name:** Siriwardena D.R.S (IT22143440) · **ProjectID:** J26-IT-396 · **Branch:** `feature/c3-yard`

Part of the *AI Powered Autonomous Smart Port Management System*.

## Overview
An AI-based decision-support system for **one container yard block (Yard Block 01)**:
56 bays × 6 rows × 4 tiers = 1,296 slots.

When a container arrives, the system:
1. **Predicts its dwell time** (how long it will stay) with a per-container machine learning model.
2. **Checks its yard type**: reefers go to powered bays, hazardous cargo to an isolated area.
3. **Recommends a zone**: Fast-Access (short stay, near the gate), Medium-Access or Long-Term.
4. **Chooses the exact slot** (block-bay-row-tier, e.g. `B01-08-4-T1`) so it does not block containers that leave sooner.
5. Lets the **yard manager accept or override** the recommendation (a reason is required).

It also **forecasts block occupancy for 14 days** and raises an **alert above 85%**.

## Problem
Containers are usually placed in the next free slot without knowing how long they will stay.
A container leaving soon can be buried under one that stays longer, so the crane must move the
containers on top first (a **reshuffle**). Reefer and hazardous containers can also end up in the
wrong place.

## Yard Block 01 layout
| Zone | Bays | Slots | Used for |
|---|---|---|---|
| Fast-Access | 1–19 | 456 | Predicted dwell < 3 days (nearest the gate) |
| Medium-Access | 20–35 | 384 | 3–7 days |
| Long-Term | 36 | 24 | > 7 days |
| Reefer | 37–46 | 240 | Refrigerated containers (powered) |
| Buffer | 47–48 | – | Kept empty to separate hazardous cargo |
| Hazardous | 49–56 | 192 | Dangerous cargo (isolated) |

## Slot rule
1. Use an **empty stack** in the recommended zone first.
2. Otherwise, use a stack that is not full **only if its top container is predicted to leave at least
   36 hours after the new one**, so the new container does not block it.
3. Use other general zones only if the recommended zone is full.

The 36-hour margin was chosen on a validation period (0 **less than a hour**, 12, 24 and 36 hours were tested).

## Models and results
Trained and tested on a real container terminal event log (~95,000 containers, Jul–Sep 2021),
with a chronological split (65 training days, 17 test days).

| Model | Purpose | Result |
|---|---|---|
| Prophet (primary) | Daily average dwell time, using container characteristics | MAPE **14.8%** (rolling 7-day) |
| ARIMA (baseline) | Daily average dwell time | MAPE 16.7% |
| XGBoost (per-container) | Dwell time of each arriving container | MAE 1.36 days, **21.5% better** than baseline |
| XGBoost (occupancy) | Containers in the block, 14 days ahead | **R² 0.86**, MAPE 7.3% (next day) |

**Stacking simulation** (real arrival and departure times, ~4,200 containers, 5 runs):

| | Random placement | AI (predicted dwell) | AI (perfect knowledge) |
|---|---|---|---|
| Reshuffles | 3,832 | **2,085** | 1,471 |
| Retrievals needing a reshuffle | 55.7% | **36.9%** | 21.5% |
| Yard-type violations | 1,166 | **0** | 0 |

**45.6% fewer reshuffles** than random placement (target was at least 25%).

## Project structure
| Folder / file | Contents |
|---|---|
| `ml-models/YardAllocation.ipynb` | Data cleaning, model training and evaluation, stacking simulation, model checks |
| `backend/yard/` | Flask API (`app.py`), yard logic (`yard_service.py`), zone and slot rules (`zone_engine.py`), model loading (`predictors.py`) |
| `backend/yard/models/` | Saved models and `model_metrics.json` |
| `backend/yard/tests/` | Automated API tests |
| `backend/yard/scripts/load_demo_data.py` | Loads demo containers for the dashboard |
| `frontend/` | React + TypeScript dashboard (8 screens) |
| `database/schema/` | PostgreSQL schema (`05_create_yard_tables.sql`, `08_extend_yard_tables.sql`) |

## Technologies
Python, pandas, Prophet, statsmodels (ARIMA), XGBoost, scikit-learn, Flask, PostgreSQL,
React, TypeScript, Vite, Tailwind CSS, Recharts.

## How to run
**1. Database:** in PostgreSQL, run `database/schema/01`, `02`, `05` and `08` in order.

**2. Backend**
```
cd backend/yard
pip install -r requirements.txt
copy .env.example .env      (then set DB_PASSWORD)
python app.py
```
The API runs on http://localhost:5001 (check http://localhost:5001/api/health).

**3. Demo data (optional):** stop the API, run `python scripts/load_demo_data.py --reset`, then start the API again.

**4. Frontend**
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

**5. Notebook:** `cd ml-models` then `python -m jupyter lab`.

## Testing
- **19 automated API tests:** `cd backend/yard` then `python -m pytest tests -v`
- **21 model checks:** notebook Cell 13 (`MODEL CHECKS: 21 / 21 passed`)

## Dashboard screens
Dashboard · New Arrival · Container Tracking · Yard Map · Dwell Prediction · Occupancy Forecast · Reports · Alerts

## Limitations and future work
- About 3 months of data, so the test period is short and yearly seasons are not captured.
- The data has no yard blocks or container types: the block is assumed to receive 25% of the
  terminal's containers, and types follow the Colombo container mix.
- Forecasts continue from the end of the data (Sep 2021) until live yard data is connected.
- Integration with the berth and gate components, daily occupancy history and measuring space
  utilization as one figure are the next steps.

## Data
- Container terminal event log (Kaggle), about 95,000 containers, Jul–Sep 2021.
- Colombo container data (container type mix and demo containers).
