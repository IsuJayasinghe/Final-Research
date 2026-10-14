# Frontend (shared)

React 19 + Vite + Tailwind + React Router. One web UI for all four components.

## Component 4 - Gate Appointment pages (`src/pages/gate/`)
The navbar has a **Driver / Gate admin** switch. It is a demo switch, not authentication; drivers are identified by truck ID.

Driver journey: check the gate -> request an appointment -> wait for approval -> upload documents -> follow the trip live.

| Route | Role | Page | Backed by |
|---|---|---|---|
| `/gate-allocation` | both | Date and hour (24-hour busy chart): per-lane forecast queue, wait, status and booked trucks. Driver's own truck/gate highlighted (`?date=&hour=&truck=`). Admin also gets lane close/reopen and rebalance | `GET /api/congestion/profile`, `/lane-view`, `/lanes/*`, `POST /api/rebalance` |
| `/gate-appointment` | driver | Pick a time from the chart, enter truck and container (weather, carrier, vessel, customs risk are derived). Sends a request that waits for approval | `POST /api/appointments` |
| `/my-trip` | driver | Stepper (request, approved, documents, gate day), live gate/queue/expected entry, delay and gate-change updates with reasons; refreshes every 10 s | `GET /api/appointments?truck_id=`, `/{id}/live`, `/{id}/notifications` |
| `/document-upload` | driver | Locked until the gate admin approves. Then upload each required document; each is OCR-checked against the booking and its template, and submitting re-scores risk | `POST /api/documents/check`, `/appointments/{id}/documents/submit` |
| `/admin/approvals` | admin | Pending requests with risk and hour load; approve, reject with reason, approve all low-risk | `POST /api/appointments/{id}/approve`, `/reject` |
| `/admin/gate-desk` | admin | Gate officer picks one of the 6 gates (remembered) and a date: that gate's approved trucks in slot order, counts, queue, closures; Check in, Complete gate process, No-show; refreshes every 10 s | `GET /api/gates/{lane}/desk`, `POST /api/appointments/{id}/check-in`, `/complete`, `/no-show` |
| `/appointments` | admin | All requests, filters, decision history | `GET /api/appointments`, `/events` |
| `/gate-optimization` | admin | Hourly slot board; inject a vessel delay / queue spike on the whole gate or one lane; shows gate changes and driver notices | `GET /api/slots`, `POST /api/reoptimize` |
| `/model-results` | admin | Model 1 / Model 2 / SHAP / framework evaluation | `GET /api/model-metrics` |

API client: `src/lib/gateApi.js` (backend at `http://localhost:8000`, see `backend/gate/`).
Other components should add their pages under `src/pages/<component>/`.

## Run
```bash
npm install
npm run dev     # http://localhost:5173
```
