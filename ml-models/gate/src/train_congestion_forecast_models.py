"""
Per-lane congestion forecasting model (Component 3, build-order step 2).

Trains one SARIMAX model per gate lane (statsmodels' ARIMA implementation,
per the spec's "Prophet or ARIMA, trained separately per gate lane" option)
to forecast `queue_length_end_of_hour`, using order (2,0,1) with a 24-hour
seasonal component (1,0,1,24) to capture the daily congestion cycle.

Each model is fit on all but the last 14 days of that lane's history and
evaluated by forecasting that 14-day holdout. The fitted (train-only) model
is what gets saved — refit on the full history before using this in
production, since the holdout period should stay unseen for evaluation.

Note: the saved .joblib files are ~2.2GB each (statsmodels pickles the full
Kalman filter/smoother history, not just the fitted params). Don't commit
them or load them in a server process. Run
src/export_congestion_forecasts.py afterward to produce a small per-lane
forecast array (a few KB) for anything that just needs forecasted values.

Usage: python src/train_congestion_forecast_models.py
"""

import json
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, root_mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "raw" / "gate_congestion_timeseries_2024_2025.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

TARGET = "queue_length_end_of_hour"
HOLDOUT_HOURS = 14 * 24  # last 14 days per lane
ORDER = (2, 0, 1)
SEASONAL_ORDER = (1, 0, 1, 24)


def load_lane_series(df: pd.DataFrame, lane_id: int) -> pd.Series:
    lane_df = df[df["gate_lane_id"] == lane_id].sort_values("timestamp")
    series = lane_df.set_index("timestamp")[TARGET]
    series.index.freq = "h"
    return series


def evaluate(y_true, y_pred) -> dict:
    return {
        "rmse": round(float(root_mean_squared_error(y_true, y_pred)), 3),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "mape": round(float(mean_absolute_percentage_error(np.maximum(y_true, 1), np.maximum(y_pred, 0))) * 100, 3),
    }


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    lane_ids = sorted(df["gate_lane_id"].unique())

    all_metrics = {}

    for lane_id in lane_ids:
        t0 = time.time()
        series = load_lane_series(df, lane_id)
        train, test = series.iloc[:-HOLDOUT_HOURS], series.iloc[-HOLDOUT_HOURS:]

        model = SARIMAX(
            train,
            order=ORDER,
            seasonal_order=SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fitted = model.fit(disp=False, maxiter=50)

        forecast = fitted.get_forecast(steps=len(test))
        preds = forecast.predicted_mean.clip(lower=0)
        metrics = evaluate(test.values, preds.values)
        metrics["fit_seconds"] = round(time.time() - t0, 1)
        all_metrics[f"lane_{lane_id}"] = metrics

        joblib.dump(fitted, MODEL_DIR / f"congestion_forecast_lane_{lane_id}.joblib")
        print(f"Lane {lane_id}: {metrics}")

    baseline_metrics = {}
    for lane_id in lane_ids:
        series = load_lane_series(df, lane_id)
        train, test = series.iloc[:-HOLDOUT_HOURS], series.iloc[-HOLDOUT_HOURS:]
        naive_pred = np.full(len(test), train.iloc[-24:].mean())
        baseline_metrics[f"lane_{lane_id}"] = evaluate(test.values, naive_pred)

    print("\nNaive baseline (last-24h mean) for comparison:")
    for lane_id in lane_ids:
        print(f"Lane {lane_id}: {baseline_metrics[f'lane_{lane_id}']}")

    with open(REPORT_DIR / "congestion_forecast_metrics.json", "w") as f:
        json.dump({"sarimax": all_metrics, "naive_baseline": baseline_metrics}, f, indent=2)

    print(f"\nSaved {len(lane_ids)} per-lane models to {MODEL_DIR}")
    print(f"Saved metrics to {REPORT_DIR / 'congestion_forecast_metrics.json'}")


if __name__ == "__main__":
    main()
