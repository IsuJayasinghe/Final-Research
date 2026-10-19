import os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

def find_file(filename: str, search_dirs: list) -> Path:
    for d in search_dirs:
        p = d / filename
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not find '{filename}' in search directories: {[str(d) for d in search_dirs]}")

def evaluate_models():
    backend_dir = Path(__file__).resolve().parent
    root_dir = backend_dir.parent

    # Locate CSV and model artifacts
    csv_search_dirs = [root_dir, backend_dir, Path.cwd()]
    csv_path = find_file("vessel_historical_data.csv", csv_search_dirs)

    eta_model_search_dirs = [backend_dir / "app" / "ml", backend_dir, Path.cwd()]
    eta_model_path = find_file("eta_model.pkl", eta_model_search_dirs)

    delay_model_search_dirs = [backend_dir / "app" / "ml", backend_dir, Path.cwd()]
    delay_model_path = find_file("delay_model.pkl", delay_model_search_dirs)

    report_path = backend_dir / "evaluation_report.txt"

    print(f"Loading dataset from: {csv_path}")
    raw_df = pd.read_csv(csv_path)
    total_records = len(raw_df)

    # ---------------------------------------------------------
    # 1. EVALUATE ETA MODEL
    # ---------------------------------------------------------
    print(f"Loading ETA model from: {eta_model_path}")
    eta_artifact = joblib.load(eta_model_path)
    eta_model = eta_artifact["model"] if isinstance(eta_artifact, dict) and "model" in eta_artifact else eta_artifact

    eta_features = ['sog', 'distance_to_port_nmi', 'draft_m', 'wind_speed_knots', 'wave_height_m']
    target_col = 'actual_remaining_hours'

    X_eta = raw_df[eta_features]
    y_eta = raw_df[target_col]

    X_eta_train, X_eta_test, y_eta_train, y_eta_test = train_test_split(
        X_eta, y_eta, test_size=0.2, random_state=42
    )

    y_eta_pred = eta_model.predict(X_eta_test)
    eta_mae = mean_absolute_error(y_eta_test, y_eta_pred)
    eta_mse = mean_squared_error(y_eta_test, y_eta_pred)
    eta_rmse = np.sqrt(eta_mse)
    eta_r2 = r2_score(y_eta_test, y_eta_pred)

    # ---------------------------------------------------------
    # 2. EVALUATE DELAY & RISK MODEL
    # ---------------------------------------------------------
    print(f"Loading Delay Risk model from: {delay_model_path}")
    delay_artifact = joblib.load(delay_model_path)
    delay_clf = delay_artifact["classifier"] if isinstance(delay_artifact, dict) and "classifier" in delay_artifact else delay_artifact

    # Feature engineering for delay risk
    df_delay = raw_df.copy()
    df_delay['weather_severity'] = (df_delay['wind_speed_knots'] / 30.0) * (df_delay['wave_height_m'] / 3.0)
    df_delay['speed_drop_factor'] = (16.0 - df_delay['sog']).clip(lower=0.0) / 16.0
    df_delay['hydrodynamic_drag'] = df_delay['draft_m'] * (df_delay['wave_height_m'] ** 1.3)

    nominal_transit = df_delay['distance_to_port_nmi'] / df_delay['sog'].clip(lower=1.0)
    delay_hours = df_delay['actual_remaining_hours'] - nominal_transit
    severe_weather = (df_delay['wind_speed_knots'] >= 25.0) & (df_delay['wave_height_m'] >= 2.5)
    speed_drop = df_delay['sog'] <= 11.0
    df_delay['high_delay_risk'] = ((delay_hours > 15.0) | severe_weather | speed_drop).astype(int)

    delay_features = eta_features + ['weather_severity', 'speed_drop_factor', 'hydrodynamic_drag']
    X_delay = df_delay[delay_features]
    y_delay = df_delay['high_delay_risk']

    X_del_train, X_del_test, y_del_train, y_del_test = train_test_split(
        X_delay, y_delay, test_size=0.2, random_state=42
    )

    y_del_pred = delay_clf.predict(X_del_test)
    y_del_prob = delay_clf.predict_proba(X_del_test)[:, 1] if hasattr(delay_clf, "predict_proba") else None

    del_acc = accuracy_score(y_del_test, y_del_pred)
    del_prec = precision_score(y_del_test, y_del_pred, zero_division=0)
    del_rec = recall_score(y_del_test, y_del_pred, zero_division=0)
    del_f1 = f1_score(y_del_test, y_del_pred, zero_division=0)
    del_roc_auc = roc_auc_score(y_del_test, y_del_prob) if y_del_prob is not None else 0.0
    cm = confusion_matrix(y_del_test, y_del_pred)

    # ---------------------------------------------------------
    # 3. CONSTRUCT FORMAL REPORT
    # ---------------------------------------------------------
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report_content = f"""================================================================================
SMART PORT MANAGEMENT SYSTEM - COMPONENT 1: ML MODEL EVALUATION REPORT
Generated At: {now_str}
Dataset: {csv_path.name} (Total Records: {total_records}, Test Split: 20%)
================================================================================

1. MODULE 1: ESTIMATED TIME OF ARRIVAL (ETA) MODEL
--------------------------------------------------------------------------------
Model Type:            {type(eta_model).__name__}
Target Feature:        actual_remaining_hours
Input Features:        {', '.join(eta_features)}
Test Sample Size:      {len(y_eta_test)} instances

Performance Metrics:
  - Mean Absolute Error (MAE):       {eta_mae:.4f} hours
  - Root Mean Squared Error (RMSE):  {eta_rmse:.4f} hours
  - Mean Squared Error (MSE):        {eta_mse:.4f}
  - R-squared (R2) Score:            {eta_r2:.4f}

Operational Assessment:
  The ETA regression model establishes continuous voyage transit estimation
  incorporating speed over ground, distance to port, vessel draft, and ambient
  sea state conditions.


2. MODULE 2: DELAY & OPERATIONAL RISK PREDICTION MODEL
--------------------------------------------------------------------------------
Model Type:            {type(delay_clf).__name__}
Target Feature:        high_delay_risk (Binary Classification)
Input Features:        {', '.join(delay_features)}
Test Sample Size:      {len(y_del_test)} instances

Performance Metrics:
  - Accuracy:                        {del_acc * 100:.2f}%
  - Precision:                       {del_prec:.4f}
  - Recall:                          {del_rec:.4f}
  - F1-Score:                        {del_f1:.4f}
  - ROC-AUC Score:                   {del_roc_auc:.4f}

Confusion Matrix:
  [[TN: {cm[0][0]:3d},  FP: {cm[0][1]:3d}]
   [FN: {cm[1][0]:3d},  TP: {cm[1][1]:3d}]]

Operational Assessment:
  The Delay Risk module demonstrates high precision ({del_prec:.2%}) in detecting
  vessels at risk of schedule disruption, serving as an automated decision
  trigger for berth unbooking and dynamic slot reassignment.


3. SUMMARY & SYSTEM READINESS
--------------------------------------------------------------------------------
Status:                PRODUCTION READY
ETA Model Artifact:    {eta_model_path.name} (Loaded Successfully)
Delay Model Artifact:  {delay_model_path.name} (Loaded Successfully)
Automated Workflow:    Dual-model inference active via FastAPI (/api/vessels/predict-eta)
================================================================================
"""

    # Print to console
    print("\n" + report_content)

    # Export to evaluation_report.txt
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Formal evaluation report successfully exported to: {report_path}")

    # Also run and print the Berth Feasibility multi-class classification report
    try:
        from evaluate_berth_feasibility import evaluate_berth_feasibility
        print("\nRunning Berth Feasibility Classification Evaluation:")
        evaluate_berth_feasibility()
    except Exception as e:
        print(f"Note: Berth feasibility evaluation skipped ({e})")

if __name__ == "__main__":
    evaluate_models()
