# SmartYard – Yard Management Dashboard

React + TypeScript dashboard for Component 3 (Smart Container Yard Allocation & Space
Utilization Optimization). It uses the yard API in `backend/yard`.

Built with Vite, Tailwind CSS, Recharts and React Router.

## Screens

| Screen | Route | Requirement |
|---|---|---|
| Dashboard | `/` | Yard overview, 7-day forecast, zone occupancy |
| Container Tracking | `/containers` | Search, filters, overstaying, departure (FR09) |
| New Arrival | `/containers/new` | AI dwell prediction, zone and slot, accept / override (FR01–FR07) |
| Dwell Prediction | `/predictions/dwell` | Prophet vs ARIMA comparison |
| Yard Occupancy | `/predictions/occupancy` | XGBoost 14-day forecast with 85% alerts (FR03, FR08) |
| Yard Map | `/yard-map` | Yard Block 01 seen from above: zones, bays and stacks |
| Reports | `/reports` | Simulation results and results vs proposal targets |
| Alerts | `/alerts` | Current and forecast capacity alerts (FR08) |

## Run

1. Start the API first (see `backend/yard/README.md`):
   ```
   cd backend/yard
   python app.py
   ```
2. In a second terminal:
   ```
   cd frontend
   npm install
   npm run dev
   ```
3. Open http://localhost:5173. The header shows **Live** when the API and database are connected.

The API address defaults to `http://localhost:5001`. To change it, copy `.env.example` to
`.env` and set `VITE_API_URL`.

## Build

```
npm run build
```
The production files are written to `dist/`.

## Notes

- Forecasts continue from the end of the training data (September 2021), so charts label
  them as Day 1, Day 2, ... rather than calendar dates.
- For a populated dashboard, load the demo data first (`backend/yard/README.md`).
