"""
Exports a compact per-lane forecast array from the fitted SARIMAX models.

The fitted SARIMAXResults objects saved by train_congestion_forecast_models.py
are enormous (~2.2GB each) because statsmodels pickles the full Kalman
filter/smoother history alongside the model. The backend only ever needs the
forecasted values themselves, so this script loads each fitted model once,
forecasts a fixed horizon beyond its training cutoff, and saves just that
array (a few KB) to data/processed/ for the backend to serve from directly.

Usage: python src/export_congestion_forecasts.py
"""

import json
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"
OUT_DIR = ROOT / "data" / "processed"

LANE_IDS = [1, 2, 3, 4, 5, 6]
HORIZON_HOURS = 24 * 7  # one week beyond each lane's training cutoff


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export = {}

    for lane in LANE_IDS:
        path = MODEL_DIR / f"congestion_forecast_lane_{lane}.joblib"
        print(f"Loading lane {lane} model...")
        fitted = joblib.load(path)
        forecast = fitted.get_forecast(steps=HORIZON_HOURS)
        values = forecast.predicted_mean.clip(lower=0).round(2).tolist()
        export[str(lane)] = values
        print(f"Lane {lane}: exported {len(values)} forecasted hours")

    out_path = OUT_DIR / "congestion_forecast.json"
    with open(out_path, "w") as f:
        json.dump(export, f)

    size_kb = out_path.stat().st_size / 1024
    print(f"\nSaved compact forecast export to {out_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
