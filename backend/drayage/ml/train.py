"""
Model Training and Evaluation Pipeline for Component 2 Drayage Travel Time Prediction.

Trains an XGBoost Regressor pipeline predicting container transit durations
(in seconds and minutes) based on terminal route distances, vehicle type,
corridor traffic congestion, and temporal shift factors.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import xgboost as xgb

# Internal ML imports
from backend.drayage.ml.data_prep import (
    DATA_DIR,
    PREPARED_CSV_DEFAULT,
    load_raw_dataset,
    prepare_features,
    save_prepared_dataset,
)

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / "travel_time_xgb.joblib"
METRICS_PATH = MODELS_DIR / "model_metrics.json"

FEATURE_COLS = [
    "Distance_Meters",
    "Vehicle_Type",
    "Route_ID",
    "Start_Zone",
    "Destination_Zone",
    "departure_hour",
    "day_of_week",
    "is_peak_hour",
    "is_night_shift",
]

CATEGORICAL_COLS = ["Vehicle_Type", "Route_ID", "Start_Zone", "Destination_Zone"]
NUMERIC_COLS = ["Distance_Meters", "departure_hour", "day_of_week", "is_peak_hour", "is_night_shift"]
TARGET_COL = "travel_time_seconds"


def load_or_create_data() -> pd.DataFrame:
    """Load pre-engineered dataset or generate it from raw inputs."""
    if PREPARED_CSV_DEFAULT.exists():
        print(f"[train] Loading prepared dataset from {PREPARED_CSV_DEFAULT.name}")
        return pd.read_csv(PREPARED_CSV_DEFAULT)

    print("[train] Prepared dataset not found, generating from raw source...")
    raw = load_raw_dataset()
    prep = prepare_features(raw)
    save_prepared_dataset(prep)
    return prep


def train_travel_time_model(
    test_size: float = 0.20,
    random_state: int = 42,
    save_artifacts: bool = True,
) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Train and evaluate the XGBoost travel time regression pipeline.
    """
    df = load_or_create_data()
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Scikit-learn Pipeline with ColumnTransformer for robust preprocessing
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_COLS),
            ("num", "passthrough", NUMERIC_COLS),
        ]
    )

    model_params = {
        "n_estimators": 250,
        "max_depth": 5,
        "learning_rate": 0.07,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "random_state": random_state,
        "n_jobs": -1,
    }

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", xgb.XGBRegressor(**model_params)),
        ]
    )

    print(f"[train] Training XGBoost regressor on {len(X_train)} training instances...")
    pipeline.fit(X_train, y_train)

    # Evaluate on Train and Test sets
    y_train_pred = pipeline.predict(X_train)
    y_test_pred = pipeline.predict(X_test)

    train_mae = float(mean_absolute_error(y_train, y_train_pred))
    train_rmse = float(np.sqrt(mean_squared_error(y_train, y_train_pred)))
    train_r2 = float(r2_score(y_train, y_train_pred))

    test_mae = float(mean_absolute_error(y_test, y_test_pred))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, y_test_pred)))
    test_r2 = float(r2_score(y_test, y_test_pred))

    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_type": "XGBoost Regressor (Pipeline)",
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "target": TARGET_COL,
        "train_metrics": {
            "mae_seconds": round(train_mae, 2),
            "rmse_seconds": round(train_rmse, 2),
            "r2_score": round(train_r2, 4),
            "mae_minutes": round(train_mae / 60.0, 3),
            "rmse_minutes": round(train_rmse / 60.0, 3),
        },
        "test_metrics": {
            "mae_seconds": round(test_mae, 2),
            "rmse_seconds": round(test_rmse, 2),
            "r2_score": round(test_r2, 4),
            "mae_minutes": round(test_mae / 60.0, 3),
            "rmse_minutes": round(test_rmse / 60.0, 3),
        },
        "hyperparameters": model_params,
        "features": {
            "categorical": CATEGORICAL_COLS,
            "numeric": NUMERIC_COLS,
            "all": FEATURE_COLS,
        },
    }

    print("\n" + "=" * 60)
    print("XGBOOST TRAVEL TIME MODEL EVALUATION")
    print("=" * 60)
    print(f"Test MAE : {test_mae:.2f} seconds ({test_mae/60.0:.2f} minutes)")
    print(f"Test RMSE: {test_rmse:.2f} seconds ({test_rmse/60.0:.2f} minutes)")
    print(f"Test R^2 : {test_r2:.4f} (Variance Explained: {test_r2*100:.1f}%)")
    print("=" * 60)

    if save_artifacts:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)
        print(f"[train] Model pipeline serialized to: {MODEL_PATH}")

        with open(METRICS_PATH, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        print(f"[train] Evaluation metrics saved to: {METRICS_PATH}")

    return pipeline, metrics


if __name__ == "__main__":
    from typing import Tuple
    train_travel_time_model()
