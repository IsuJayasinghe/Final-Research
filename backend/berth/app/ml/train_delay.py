import os
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    mean_absolute_error,
    mean_squared_error
)

BASE_FEATURES = ['sog', 'distance_to_port_nmi', 'draft_m', 'wind_speed_knots', 'wave_height_m']
ALL_FEATURES = BASE_FEATURES + ['weather_severity', 'speed_drop_factor', 'hydrodynamic_drag']

def get_paths():
    current_file = Path(__file__).resolve()
    ml_dir = current_file.parent
    app_dir = ml_dir.parent
    backend_dir = app_dir.parent
    root_dir = backend_dir.parent

    # Search paths for vessel historical data
    search_dirs = [backend_dir, root_dir, backend_dir.parent, Path.cwd()]
    csv_path = None
    for d in search_dirs:
        candidate = d / "vessel_historical_data.csv"
        if candidate.exists():
            csv_path = candidate
            break

    db_path = backend_dir / "smart_port.db"

    model_path_ml = ml_dir / "delay_model.pkl"
    model_path_backend = backend_dir / "delay_model.pkl"

    return csv_path, db_path, model_path_ml, model_path_backend

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes operational and environmental features for delay risk modeling."""
    data = df.copy()

    # Weather severity index (non-linear interaction between wind and wave)
    data['weather_severity'] = (data['wind_speed_knots'] / 30.0) * (data['wave_height_m'] / 3.0)

    # Speed drop factor (measuring drop below normal cruising speed of 16 knots)
    data['speed_drop_factor'] = (16.0 - data['sog']).clip(lower=0.0) / 16.0

    # Hydrodynamic drag estimate (draft displacement times wave power)
    data['hydrodynamic_drag'] = data['draft_m'] * (data['wave_height_m'] ** 1.3)

    return data

def train_and_save_delay_model():
    csv_path, db_path, model_path_ml, model_path_backend = get_paths()

    if csv_path and csv_path.exists():
        print(f"Loading vessel historical data from CSV: {csv_path}")
        raw_df = pd.read_csv(csv_path)
    elif db_path.exists():
        import sqlite3
        print(f"Loading vessel historical data from SQLite: {db_path}")
        conn = sqlite3.connect(db_path)
        raw_df = pd.read_sql("SELECT * FROM vessel_historical_data", conn)
        conn.close()
    else:
        raise FileNotFoundError(f"Dataset not found at CSV or database: {db_path}")

    clean_df = engineer_features(raw_df)

    # Calculate nominal kinematics time (distance / speed)
    nominal_transit_hours = clean_df['distance_to_port_nmi'] / clean_df['sog'].clip(lower=1.0)
    delay_hours = clean_df['actual_remaining_hours'] - nominal_transit_hours
    clean_df['delay_hours'] = delay_hours

    # Define high delay risk target:
    # A vessel is classified as high delay risk if delay exceeds 15 hours
    # OR if extreme wind (>25 kts) and waves (>2.5m) occur together.
    severe_weather = (clean_df['wind_speed_knots'] >= 25.0) & (clean_df['wave_height_m'] >= 2.5)
    speed_drop = clean_df['sog'] <= 11.0
    clean_df['high_delay_risk'] = ((delay_hours > 15.0) | severe_weather | speed_drop).astype(int)

    X = clean_df[ALL_FEATURES]
    y_class = clean_df['high_delay_risk']
    y_reg = clean_df['delay_hours'].clip(lower=0.0)

    # Train / test split
    X_train, X_test, y_train_cls, y_test_cls, y_train_reg, y_test_reg = train_test_split(
        X, y_class, y_reg, test_size=0.2, random_state=42
    )

    print("Training Delay Risk Classification Model (Random Forest)...")
    clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=10,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        class_weight='balanced',
        n_jobs=-1
    )
    clf.fit(X_train, y_train_cls)

    y_pred_cls = clf.predict(X_test)
    y_prob_cls = clf.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test_cls, y_pred_cls)
    prec = precision_score(y_test_cls, y_pred_cls, zero_division=0)
    rec = recall_score(y_test_cls, y_pred_cls, zero_division=0)
    f1 = f1_score(y_test_cls, y_pred_cls, zero_division=0)
    roc_auc = roc_auc_score(y_test_cls, y_prob_cls)

    print("--- Delay Classification Metrics ---")
    print(f"Accuracy:  {acc * 100:.2f}%")
    print(f"Precision: {prec:.3f}")
    print(f"Recall:    {rec:.3f}")
    print(f"F1-Score:  {f1:.3f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")

    print("\nTraining Delay Magnitude Regressor (Gradient Boosting)...")
    reg = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.08,
        random_state=42
    )
    reg.fit(X_train, y_train_reg)

    y_pred_reg = reg.predict(X_test)
    mae = mean_absolute_error(y_test_reg, y_pred_reg)
    rmse = np.sqrt(mean_squared_error(y_test_reg, y_pred_reg))

    print("--- Delay Magnitude Regression Metrics ---")
    print(f"MAE:  {mae:.2f} hours")
    print(f"RMSE: {rmse:.2f} hours")

    # Fit final models on full dataset
    print("\nFitting final delay risk models on full dataset...")
    clf.fit(X, y_class)
    reg.fit(X, y_reg)

    model_artifact = {
        'classifier': clf,
        'regressor': reg,
        'feature_columns': ALL_FEATURES,
        'base_features': BASE_FEATURES,
        'metrics': {
            'accuracy': float(acc),
            'f1': float(f1),
            'roc_auc': float(roc_auc),
            'mae_delay_hours': float(mae)
        },
        'risk_thresholds': {
            'low': 0.35,
            'moderate': 0.60,
            'high': 0.80,
            'reassignment_trigger_prob': 0.65,
            'reassignment_trigger_hours': 2.5
        },
        'metadata': {
            'model_type': 'RandomForestClassifier + GradientBoostingRegressor',
            'train_samples': len(clean_df),
            'description': 'Predicts delay risk probability and magnitude to trigger automated berth reassignments.'
        }
    }

    # Save to both paths
    for save_path in [model_path_ml, model_path_backend]:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_artifact, save_path)
        print(f"Saved delay model artifact to: {save_path}")

    return model_artifact

if __name__ == "__main__":
    train_and_save_delay_model()
