# Frontend (shared)

React 19 + Vite + Tailwind + React Router. One web UI for all four components.

## Component 4 — Gate Appointment pages (`src/pages/gate/`)
| Route | Page | Backed by |
|---|---|---|
| `/gate-appointment` | Booking form -> lane, gate entry, clearance time, model inputs | `POST /api/assign-appointment` (clearance + congestion models) |
| `/gate-allocation` | Per-lane queue and wait monitoring | `GET /api/congestion` |
| `/document-upload` | Pre-clearance document upload | simulated validation (no model yet) |

API client: `src/lib/gateApi.js` (backend at `http://localhost:8000`, see `backend/gate/`).
Other components should add their pages under `src/pages/<component>/`.

## Run
```bash
npm install
npm run dev     # http://localhost:5173
```
