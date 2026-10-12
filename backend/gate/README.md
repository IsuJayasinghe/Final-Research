# Component 4 — Gate Appointment API

FastAPI service for the AI-Powered Gate Appointment System. Routes live in an
`APIRouter` (`router.py`) so the shared backend can mount them later; `main.py`
runs the component standalone.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/assign-appointment` | Forecast all 6 lanes at the planned arrival hour, pick the lowest-queue lane, predict clearance time, return gate entry and departure |
| POST | `/api/predict-clearance` | Clearance-time model on its own |
| GET | `/api/congestion?at=YYYY-MM-DDTHH:MM` | Per-lane forecast queue and wait for a chosen hour |

## Model inputs (from the booking form)
container type, cargo category, carrier, customs risk, missing documents,
carrier reliability, planned arrival date and hour. Invalid values are rejected
with HTTP 422.

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
- Bookings are not persisted yet; they will go to `gate.gate_appointments` (see `database/schema/06_create_gate_tables.sql`).
