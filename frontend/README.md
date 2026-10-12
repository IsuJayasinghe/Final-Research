# Frontend (shared)

React 19 + Vite + Tailwind + React Router. One web UI for all four components.

## Component 4 — Gate Appointment pages (`src/pages/gate/`)
| Route | Page | Backed by |
|---|---|---|
| `/gate-appointment` | Booking form -> no-show risk (SHAP reasons), overbooking decision, lane, clearance time; confirm/cancel | `POST /api/appointments` |
| `/appointments` | Saved bookings, confirm/cancel, decision history | `GET /api/appointments`, `/events` |
| `/gate-optimization` | Hourly slot board; inject vessel delay / queue spike and re-optimize unconfirmed bookings | `GET /api/slots`, `POST /api/reoptimize` |
| `/gate-allocation` | Per-lane queue and wait monitoring | `GET /api/congestion` |
| `/model-results` | Model 1 / Model 2 / SHAP / framework evaluation | `GET /api/model-metrics` |
| `/document-upload` | Upload the 6-7 required documents; each is OCR-checked against the booking, fields and issues shown, and submitting re-scores risk | `POST /api/documents/check`, `/appointments/{id}/documents/submit` |

API client: `src/lib/gateApi.js` (backend at `http://localhost:8000`, see `backend/gate/`).
Other components should add their pages under `src/pages/<component>/`.

## Run
```bash
npm install
npm run dev     # http://localhost:5173
```
