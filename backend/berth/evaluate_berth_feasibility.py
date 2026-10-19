from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

# Standard target categories requested by project specification
CLASSES = ['Conditionally Feasible', 'Feasible', 'Infeasible']

def find_file(filename: str, search_dirs: list) -> Path:
    for d in search_dirs:
        p = d / filename
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not find '{filename}' in search directories: {[str(d) for d in search_dirs]}")

def generate_feasibility_dataset(vessel_csv_path: Path, berth_csv_path: Path) -> pd.DataFrame:
    """
    Constructs vessel-berth berthing interaction pairs and assigns
    ground truth operational feasibility categories based on port nautical guidelines:
      - Infeasible: Physical dimension violation (draft > max_draft or length > max_length)
                    or extreme weather (wind >= 28 kts or waves >= 3.0m).
      - Conditionally Feasible: Tight safety margins (draft clearance < 1.0m, length clearance < 25m)
                                or elevated environmental conditions (wind >= 18 kts, waves >= 1.8m)
                                requiring tug assistance / tidal window.
      - Feasible: Ample physical safety clearance and calm sea conditions.
    """
    df_vessel = pd.read_csv(vessel_csv_path)
    df_berth = pd.read_csv(berth_csv_path)

    # Standard vessel length estimation based on vessel class
    length_map = {
        'Container Ship': 350.0,
        'Bulk Carrier': 280.0,
        'Oil Tanker': 260.0,
        'Oil/Chemical Tanker': 220.0,
        'General Cargo Ship': 160.0
    }
    df_vessel['vessel_length_m'] = df_vessel['vessel_type'].map(length_map).fillna(250.0)

    # Clean and rename berth columns
    df_berth = df_berth.rename(columns={
        'Berth ID': 'berth_id',
        'Terminal Name': 'terminal_name',
        'Max Draft (m)': 'max_draft_m',
        'Max Length (m)': 'max_length_m',
        'Crane Count': 'crane_count',
        'Crane Handling Rate (TEU/hr)': 'crane_handling_rate'
    })

    # Sample representative interactions across fleet and terminal berths
    np.random.seed(42)
    sampled_vessels = df_vessel.sample(n=1200, random_state=42, replace=True).reset_index(drop=True)
    sampled_berths = df_berth.sample(n=1200, random_state=42, replace=True).reset_index(drop=True)

    df_pairs = pd.concat([
        sampled_vessels[['vessel_name', 'vessel_type', 'draft_m', 'vessel_length_m', 'wind_speed_knots', 'wave_height_m', 'sog']],
        sampled_berths[['berth_id', 'terminal_name', 'max_draft_m', 'max_length_m', 'crane_count', 'crane_handling_rate']]
    ], axis=1)

    df_pairs['draft_clearance'] = df_pairs['max_draft_m'] - df_pairs['draft_m']
    df_pairs['length_clearance'] = df_pairs['max_length_m'] - df_pairs['vessel_length_m']

    def assign_category(row):
        # 1. Infeasible
        if (row['draft_clearance'] < 0.0 or
            row['length_clearance'] < 0.0 or
            row['wind_speed_knots'] >= 28.0 or
            row['wave_height_m'] >= 3.0):
            return 'Infeasible'
        # 2. Conditionally Feasible
        elif (row['draft_clearance'] < 1.0 or
              row['length_clearance'] < 25.0 or
              row['wind_speed_knots'] >= 18.0 or
              row['wave_height_m'] >= 1.8):
            return 'Conditionally Feasible'
        # 3. Feasible
        else:
            return 'Feasible'

    df_pairs['feasibility'] = df_pairs.apply(assign_category, axis=1)
    return df_pairs

def evaluate_berth_feasibility():
    backend_dir = Path(__file__).resolve().parent
    root_dir = backend_dir.parent

    # Search for input CSV files
    search_dirs = [root_dir, backend_dir, Path.cwd()]
    vessel_csv = find_file("vessel_historical_data.csv", search_dirs)
    berth_csv = find_file("berth_characteristics.csv", search_dirs)

    # Model save paths
    model_dir = backend_dir / "app" / "ml"
    model_path = model_dir / "berth_feasibility_model.pkl"

    # Build dataset
    data = generate_feasibility_dataset(vessel_csv, berth_csv)
    features = [
        'draft_m', 'vessel_length_m', 'wind_speed_knots', 'wave_height_m',
        'max_draft_m', 'max_length_m', 'draft_clearance', 'length_clearance'
    ]
    X = data[features]
    y = data['feasibility']

    # Stratified test split (20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Load or fit Random Forest Classifier
    if model_path.exists():
        model_artifact = joblib.load(model_path)
        clf = model_artifact["model"] if isinstance(model_artifact, dict) and "model" in model_artifact else model_artifact
    else:
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=4,
            random_state=42
        )
        clf.fit(X_train, y_train)
        # Save model artifact
        model_artifact = {
            "model": clf,
            "feature_columns": features,
            "classes": CLASSES,
            "trained_at": datetime.now(timezone.utc).isoformat()
        }
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_artifact, model_path)
        joblib.dump(model_artifact, backend_dir / "berth_feasibility_model.pkl")

    # Predict on test data
    y_pred = clf.predict(X_test)

    # Compute overall and weighted metrics
    acc = accuracy_score(y_test, y_pred)
    w_prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    w_rec = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    w_f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

    # Generate Scikit-Learn classification report matching CLASSES order
    sk_report = classification_report(
        y_test,
        y_pred,
        labels=CLASSES,
        target_names=CLASSES,
        digits=2
    )

    # Print output matching standard formatting
    print("=" * 70)
    print("Model: Random Forest")
    print("=" * 70)
    print(f"Overall Accuracy:    {acc:.4f} ({acc * 100:.2f}%)")
    print(f"Weighted Precision:  {w_prec:.4f}")
    print(f"Weighted Recall:     {w_rec:.4f}")
    print(f"Weighted F1-Score:   {w_f1:.4f}")
    print("-" * 70)
    print("Classification Report:")
    print(sk_report)
    print("=" * 70)

    # Export report to file
    report_file = backend_dir / "berth_feasibility_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("Model: Random Forest\n")
        f.write("=" * 70 + "\n")
        f.write(f"Overall Accuracy:    {acc:.4f} ({acc * 100:.2f}%)\n")
        f.write(f"Weighted Precision:  {w_prec:.4f}\n")
        f.write(f"Weighted Recall:     {w_rec:.4f}\n")
        f.write(f"Weighted F1-Score:   {w_f1:.4f}\n")
        f.write("-" * 70 + "\n")
        f.write("Classification Report:\n")
        f.write(sk_report + "\n")
        f.write("=" * 70 + "\n")

    return {
        "model_name": "Random Forest",
        "accuracy": acc,
        "weighted_precision": w_prec,
        "weighted_recall": w_rec,
        "weighted_f1": w_f1,
        "classification_report": sk_report
    }

if __name__ == "__main__":
    evaluate_berth_feasibility()
