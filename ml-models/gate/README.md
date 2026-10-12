# Component 4 â€” Gate Appointment ML models

| Model | Script | Output |
|---|---|---|
| Clearance time (XGBoost, Random Forest compared) | `src/train_clearance_time_model.py` | `models/clearance_time_model.joblib`, `reports/clearance_time_metrics.json` |
| Per-lane congestion forecast (SARIMAX, 24h seasonality) | `src/train_congestion_forecast_models.py` | `reports/congestion_forecast_metrics.json` |
| No-show / late-arrival risk (LR baseline vs XGBoost, SHAP) | `src/generate_booking_data.py`, `src/train_noshow_model.py` | `models/noshow_model.joblib`, `reports/noshow_model_metrics.json`, `reports/noshow_shap_importance.*` |
| End-to-end framework evaluation (simulation) | `src/evaluate_framework.py` | `reports/framework_evaluation.json/.png` |
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

## Framework evaluation (plan section 7)
60-day gate simulation; demand and outcomes sampled from the held-out booking period,
6 lanes, real clearance durations. Static TAS vs blind +20% overbooking vs the framework
(no-show-aware expected-arrivals rule), same days for every policy.

| Slot capacity | Static served/day | Framework served/day | Extra avg wait | Blind +20% extra wait |
|---|---|---|---|---|
| 12 (scarce) | 234.8 | 244.6 (+4.2%) | +0.1 min | +0.5 min (p90 3.0 vs 0.35) |
| 16 (headline) | 266.4 | 271.8 (+2.0%) | +0.4 min | +1.6 min (p90 11.1 vs 5.8) |
| 18-20 (generous) | ~273-274 | ~274 | no gain | no gain |

Reading: the framework recovers most of the capacity lost to no-shows without the waiting
penalty of blind overbooking, and it matters most when slots are scarce relative to demand.
Slot adherence is unchanged. Limits: synthetic data, shared-queue gate model, steady-state only
(re-optimization after disruptions is covered by backend tests and the demo).

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
python src/evaluate_framework.py
python src/train_congestion_forecast_models.py   # slow; writes ~2.2 GB per lane (not committed)
python src/export_congestion_forecasts.py
```
