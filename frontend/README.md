# Frontend (shared)

React 19 + Vite + Tailwind + React Router. One web UI for all four components.

## Component 4 — Gate Appointment pages (`src/pages/gate/`)
| Route | Page | Backed by |
|---|---|---|
| `/gate-appointment` | Booking form (only who/what/when is typed: weather, carrier reliability, vessel, customs risk and missing documents are derived) -> no-show risk (SHAP reasons), overbooking decision, lane, clearance time; confirm/cancel | `POST /api/appointments` |
| `/appointments` | Saved bookings, confirm/cancel, decision history | `GET /api/appointments`, `/events` |
| `/gate-optimization` | Hourly slot board; inject vessel delay / queue spike and re-optimize unconfirmed bookings | `GET /api/slots`, `POST /api/reoptimize` |
| `/gate-allocation` | Pick a date and hour (24-hour busy chart, busiest/quietest shortcuts): per-lane forecast queue, wait, status and the real booked trucks on each lane; shows active disruptions | `GET /api/congestion/profile`, `GET /api/lane-view` |
| `/model-results` | Model 1 / Model 2 / SHAP / framework evaluation | `GET /api/model-metrics` |
| `/document-upload` | Upload the 6-7 required documents; each is OCR-checked against the booking and its template ("must contain" before upload, a field-by-field completeness checklist after), and submitting re-scores risk | `POST /api/documents/check`, `/appointments/{id}/documents/submit` |

API client: `src/lib/gateApi.js` (backend at `http://localhost:8000`, see `backend/gate/`).
Other components should add their pages under `src/pages/<component>/`.

## Run
```bash
npm install
npm run dev     # http://localhost:5173
```
