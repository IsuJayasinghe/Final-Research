# Component 4 — Gate Appointment ML models

| Model | Script | Output |
|---|---|---|
| Clearance time (XGBoost, Random Forest compared) | `src/train_clearance_time_model.py` | `models/clearance_time_model.joblib`, `reports/clearance_time_metrics.json` |
| Per-lane congestion forecast (SARIMAX, 24h seasonality) | `src/train_congestion_forecast_models.py` | `reports/congestion_forecast_metrics.json` |
| Compact forecast export for the API | `src/export_congestion_forecasts.py` | `data/processed/congestion_forecast.json` |

## Results (chronological hold-out)
- Clearance time: XGBoost RMSE 3.0 min vs 11.1 for a mean baseline.
- Congestion: SARIMAX beats the naive baseline on RMSE for all 6 lanes.

## Data
Raw datasets are **not** committed (see `docs/data-management.md`). Place these
files locally in `data/raw/` before training:
- `gate_document_clearance_dataset_2024_2025.csv`
- `gate_congestion_timeseries_2024_2025.csv`

The datasets are synthetic, generated under documented assumptions.

## Run
```bash
pip install -r requirements.txt
python src/train_clearance_time_model.py
python src/train_congestion_forecast_models.py   # slow; writes ~2.2 GB per lane (not committed)
python src/export_congestion_forecasts.py
```
