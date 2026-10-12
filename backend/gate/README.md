# Component 4 — Gate Appointment API

FastAPI service for the AI-Powered Gate Appointment System. Routes live in an
`APIRouter` (`router.py`) so the shared backend can mount them later; `main.py`
runs the component standalone.

## What it does
1. **Model 2** scores each booking: P(on time / late / no-show), with SHAP reasons (`noshow.py`).
2. **Overbooking rule** (`scheduler.py`): a slot may exceed capacity while *expected arrivals*
   (sum of 1 - no-show risk) stay within capacity, up to a hard cap (`GATE_MAX_OVERBOOK`).
3. **Model 1** forecasts every lane; the lowest-queue lane and the cheapest nearby slot are chosen.
4. **Clearance model** predicts time at the gate; the booking is saved with its reasons (`service.py`).
5. **Re-optimization**: after a vessel delay / queue spike only unconfirmed bookings are reshuffled with an
   integer program (PuLP/CBC); confirmed bookings stay fixed and every move is explained.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/appointments` | Score risk, pick slot (overbooking rule) and lane, predict clearance, save |
| GET | `/api/appointments` | List saved appointments |
| GET | `/api/appointments/{id}/events` | Audit trail of assignments, moves and status changes |
| POST | `/api/appointments/{id}/confirm` / `/cancel` | Lifecycle |
| POST | `/api/reoptimize` | Apply a disruption (vessel delay hours, queue spike %, window, start) and re-optimize |
| DELETE | `/api/disruption` | Clear the active disruption |
| GET | `/api/slots?date=` | Hourly slot load: bookings, expected arrivals, capacity, forecast wait |
| GET | `/api/model-metrics` | Evaluation reports for the UI results page |
| POST | `/api/assign-appointment` | Original single-shot lane+slot assignment (no persistence) |
| POST | `/api/predict-clearance` | Clearance-time model on its own |
| GET | `/api/congestion?at=` | Per-lane forecast queue and wait for a chosen hour |

## Storage
By default bookings live in memory. To save them in the shared PostgreSQL database:
1. Apply `database/migrations/001_gate_appointment_predictions.sql` (additive; adds prediction columns,
   `gate.gate_appointment_events` and the six `GATE-n` lanes).
2. Copy `.env.example` to `.env` and set `DATABASE_URL` (never commit `.env`).
`GET /` reports the active `storage` (`memory` or `postgresql`).

## Tests
```bash
python -m pytest tests -q                    # memory repository
TEST_DATABASE_URL=postgresql://... python -m pytest tests -q   # also runs the PostgreSQL contract tests
```

## Run
```bash
cd backend/gate
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```
Docs at `http://localhost:8000/docs`. Models are produced by `ml-models/gate/`.

## Known limits
- Forecast covers one week after the training cutoff; a chosen date maps onto it by hour-of-week.
- Wait time = forecast queue x 5.5 min (no separate model).
- A disruption is held in the running process (cleared by `DELETE /api/disruption` or a restart).
- Slot capacity (`GATE_SLOT_CAPACITY`, default 6 for demos) is configurable; the evaluation uses 16.
