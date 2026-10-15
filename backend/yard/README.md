# Component 3 – Smart Container Yard Allocation API

Flask API for dwell-time prediction, yard occupancy forecasting, zone recommendation and
slot allocation. The trained models in `models/` are produced by
`ml-models/YardAllocation.ipynb` (Cell 12).

## Files

| File | Purpose |
|---|---|
| `app.py` | API endpoints |
| `yard_service.py` | Allocation, accept/override, departure, search and summaries |
| `zone_engine.py` | Zone rules and slot assignment (shared with the notebook) |
| `predictors.py` | Loads the models; dwell, occupancy and per-container predictions |
| `db.py` | Database settings (from `.env`) |
| `scripts/load_demo_data.py` | Loads demo containers for the dashboard |
| `tests/test_api.py` | API tests |

## Setup

1. Install the packages:
   ```
   pip install -r requirements.txt
   ```
2. Create the database tables (PostgreSQL). In pgAdmin's Query Tool on your database, run
   these files from `database/schema/` in order: `01_create_schemas.sql`,
   `02_create_common_tables.sql`, `05_create_yard_tables.sql`, `08_extend_yard_tables.sql`.
3. Copy `.env.example` to `.env` and set `DB_PASSWORD` (and `DB_NAME` if it is not `smart_port_db`).

## Run

```
python app.py
```
The API runs on http://localhost:5001 – open http://localhost:5001/api/health to check it.

## Demo data (optional)

Loads 5,000 real-mix Colombo containers over the last 7 days (about one minute).
**`--reset` deletes all containers and allocations in the yard tables first.**
Stop the API, run the loader, then start the API again:
```
python scripts/load_demo_data.py --reset
```

## Tests

```
python -m pytest tests -q
```

## Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/containers/arrival` | Predict dwell, recommend a zone and reserve a slot |
| POST | `/api/allocations/<id>/accept` | Accept the recommendation (FR07) |
| POST | `/api/allocations/<id>/override` | Move to another zone with a reason (FR07) |
| POST | `/api/containers/<id>/depart` | Container leaves; containers on top are relocated |
| GET | `/api/containers` | Search and filter (`search`, `type`, `zone`, `status`) (FR09) |
| GET | `/api/containers/<id>` | One container's slot and status |
| GET | `/api/yard/zones` | Zone, block and stack occupancy |
| GET | `/api/dashboard/summary` | Dashboard figures |
| GET | `/api/predict-dwell` | Prophet and ARIMA forecasts |
| GET | `/api/occupancy` | XGBoost occupancy forecast with 85% alerts (FR03, FR08) |
| GET | `/api/alerts` | Current and forecast capacity alerts |
| GET | `/api/reshuffling-stats`, `/api/models/metrics` | Evaluation results |
