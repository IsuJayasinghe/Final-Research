# Component 4 â€” Gate Appointment ML models

| Model | Script | Output |
|---|---|---|
| Clearance time (XGBoost, Random Forest compared) | `src/train_clearance_time_model.py` | `models/clearance_time_model.joblib`, `reports/clearance_time_metrics.json` |
| Per-lane congestion forecast (SARIMAX, 24h seasonality) | `src/train_congestion_forecast_models.py` | `reports/congestion_forecast_metrics.json` |
| No-show / late-arrival risk (LR baseline vs XGBoost, SHAP) | `src/generate_booking_data.py`, `src/train_noshow_model.py` | `models/noshow_model.joblib`, `reports/noshow_model_metrics.json`, `reports/noshow_shap_importance.*` |
| Compact forecast export for the API | `src/export_congestion_forecasts.py` | `data/processed/congestion_forecast.json` |

## Results (chronological hold-out)
- Clearance time: XGBoost RMSE 3.0 min vs 11.1 for a mean baseline.
- Congestion: SARIMAX beats the naive baseline on RMSE for all 6 lanes.

## Model 2 — no-show / late-arrival (core novelty)
Predicts P(on_time), P(late), P(no_show) per booking from carrier history, lead time,
booked hour, weather, traffic, vessel delay, customs risk and missing documents.
- Chronological split (80/20); model chosen on a validation slice, not the test set.
- Class-balanced models are reported for recall; the **serving model is trained
  without class weights** so its probabilities are calibrated for the overbooking
  layer (mean predicted no-show 8.0% vs 8.4% observed).
- No-show ROC-AUC about 0.70-0.74 and precision-recall AUC about 2.7x the base rate;
  SHAP drivers: missing documents, carrier reliability, booking lead time.
- Data is synthetic (`generate_booking_data.py`, assumptions documented in the script).

## Data
Raw datasets are **not** committed (see `docs/data-management.md`). Place these
files locally in `data/raw/` before training:
- `gate_document_clearance_dataset_2024_2025.csv`
- `gate_congestion_timeseries_2024_2025.csv`
- `gate_booking_noshow_dataset_2024_2025.csv` (create with `python src/generate_booking_data.py`)

The datasets are synthetic, generated under documented assumptions.

## Run
```bash
pip install -r requirements.txt
python src/train_clearance_time_model.py
python src/generate_booking_data.py
python src/train_noshow_model.py
python src/train_congestion_forecast_models.py   # slow; writes ~2.2 GB per lane (not committed)
python src/export_congestion_forecasts.py
```
