"""
Clearance time prediction model (Component 3, build-order step 1).

Trains an XGBoost regressor to predict `clearance_duration_minutes` for a
truck at gate clearance, using truck/cargo/document/queue features known at
or before the start of clearance. A Random Forest is trained alongside as
the spec's alternative model, for comparison.

Raw data is not tracked in git (see docs/data-management.md); place
gate_document_clearance_dataset_2024_2025.csv in ml-models/gate/data/raw/.

Usage: python src/train_clearance_time_model.py
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "raw" / "gate_document_clearance_dataset_2024_2025.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

TARGET = "clearance_duration_minutes"

CATEGORICAL_FEATURES = [
    "day_of_week",
    "container_type",
    "cargo_category",
    "carrier_company",
    "customs_risk_flag",
]
NUMERIC_FEATURES = [
    "arrival_hour",
    "carrier_past_reliability_score",
    "missing_documents_count",
    "queue_length_at_arrival",
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# Fields intentionally excluded from the feature set:
#   gate_lane_assigned          -> the lane is what the downstream MIP assignment
#                                   engine decides; using it as an input here would
#                                   make clearance-time prediction depend on an
#                                   output of a later stage in the pipeline.
#   wait_time_before_clearance_minutes -> near-duplicate signal of
#                                   queue_length_at_arrival (r=0.94 in this dataset)
#                                   and not known far enough ahead of clearance to
#                                   be useful for appointment planning.
#   clearance_start_time / clearance_end_time -> these define the target itself.


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df["arrival_hour"] = pd.to_datetime(df["arrival_time"], format="%H:%M").dt.hour
    return df


def temporal_split(df: pd.DataFrame, test_frac: float = 0.15):
    df = df.sort_values("date").reset_index(drop=True)
    split_idx = int(len(df) * (1 - test_frac))
    return df.iloc[:split_idx], df.iloc[split_idx:]


def build_pipeline(model) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="passthrough",
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def evaluate(y_true, y_pred) -> dict:
    return {
        "rmse": round(float(root_mean_squared_error(y_true, y_pred)), 3),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "mape": round(float(mean_absolute_percentage_error(y_true, y_pred)) * 100, 3),
    }


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    train_df, test_df = temporal_split(df)
    print(f"Train rows: {len(train_df)} ({train_df['date'].min().date()} - {train_df['date'].max().date()})")
    print(f"Test rows:  {len(test_df)} ({test_df['date'].min().date()} - {test_df['date'].max().date()})")

    X_train, y_train = train_df[FEATURES], train_df[TARGET]
    X_test, y_test = test_df[FEATURES], test_df[TARGET]

    # Naive baseline: predict the training-set mean for every row.
    baseline_pred = np.full_like(y_test, fill_value=y_train.mean(), dtype=float)
    baseline_metrics = evaluate(y_test, baseline_pred)
    print("\nBaseline (mean predictor):", baseline_metrics)

    results = {"baseline_mean": baseline_metrics}

    models = {
        "xgboost": XGBRegressor(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=12,
            random_state=42,
            n_jobs=-1,
        ),
    }

    best_name, best_pipeline, best_rmse = None, None, float("inf")

    for name, model in models.items():
        pipeline = build_pipeline(model)
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
        metrics = evaluate(y_test, preds)
        results[name] = metrics
        print(f"\n{name}:", metrics)

        if metrics["rmse"] < best_rmse:
            best_name, best_pipeline, best_rmse = name, pipeline, metrics["rmse"]

    # Feature importance from the tree model inside the best pipeline.
    fitted_model = best_pipeline.named_steps["model"]
    feature_names = best_pipeline.named_steps["preprocess"].get_feature_names_out()
    importance_df = (
        pd.DataFrame({"feature": feature_names, "importance": fitted_model.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    importance_df.to_json(REPORT_DIR / "clearance_feature_importance.json", orient="records", indent=2)

    print(f"\nBest model: {best_name} (RMSE={best_rmse})")
    print("\nTop features:")
    print(importance_df.head(10).to_string(index=False))

    joblib.dump(best_pipeline, MODEL_DIR / "clearance_time_model.joblib")
    with open(REPORT_DIR / "clearance_time_metrics.json", "w") as f:
        json.dump({"best_model": best_name, **results}, f, indent=2)

    print(f"\nSaved model to {MODEL_DIR / 'clearance_time_model.joblib'}")
    print(f"Saved metrics to {REPORT_DIR / 'clearance_time_metrics.json'}")


if __name__ == "__main__":
    main()
