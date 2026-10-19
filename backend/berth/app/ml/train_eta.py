import os
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

FEATURE_COLUMNS = ['sog', 'distance_to_port_nmi', 'draft_m', 'wind_speed_knots', 'wave_height_m']
TARGET_COLUMN = 'actual_remaining_hours'

def get_paths():
    current_file = Path(__file__).resolve()
    ml_dir = current_file.parent
    app_dir = ml_dir.parent
    backend_dir = app_dir.parent
    root_dir = backend_dir.parent

    # CSV path in root
    csv_path = root_dir / "vessel_historical_data.csv"
    if not csv_path.exists():
        # Fallback check in current working directory
        csv_path = Path("vessel_historical_data.csv").resolve()

    # Destination paths for model artifact
    model_path_ml = ml_dir / "eta_model.pkl"
    model_path_backend = backend_dir / "eta_model.pkl"

    return csv_path, model_path_ml, model_path_backend

def train_and_save_model():
    csv_path, model_path_ml, model_path_backend = get_paths()
    print(f"Loading vessel historical data from: {csv_path}")

    if not csv_path.exists():
        raise FileNotFoundError(f"Historical dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)
    print(f"Dataset shape: {df.shape}")

    # Check for missing values in features and target
    required_cols = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in dataset: {missing_cols}")

    clean_df = df[required_cols].dropna()
    print(f"Clean rows after dropping nulls: {len(clean_df)}")

    X = clean_df[FEATURE_COLUMNS]
    y = clean_df[TARGET_COLUMN]

    # Split dataset into train and test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("Training RandomForestRegressor model...")
    model = RandomForestRegressor(
        n_estimators=150,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Evaluate performance
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    print("--- Model Evaluation Metrics ---")
    print(f"Mean Absolute Error (MAE): {mae:.3f} hours")
    print(f"Root Mean Squared Error (RMSE): {rmse:.3f} hours")
    print(f"R² Score: {r2:.4f}")

    # Fit final model on complete clean dataset for production deployment
    print("Fitting model on full dataset for maximum generalization...")
    model.fit(X, y)

    # Prepare model artifact package
    model_artifact = {
        'model': model,
        'feature_columns': FEATURE_COLUMNS,
        'target_column': TARGET_COLUMN,
        'metrics': {
            'mae': float(mae),
            'rmse': float(rmse),
            'r2': float(r2)
        },
        'metadata': {
            'model_type': 'RandomForestRegressor',
            'train_samples': len(clean_df),
            'n_estimators': 150
        }
    }

    # Save to both Backend/app/ml/eta_model.pkl and Backend/eta_model.pkl
    for save_path in [model_path_ml, model_path_backend]:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_artifact, save_path)
        print(f"Saved trained model artifact to: {save_path}")

    return model_artifact

if __name__ == "__main__":
    train_and_save_model()
