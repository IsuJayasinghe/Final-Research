"""
Data Preparation and Feature Engineering for Component 2 Drayage Travel Time Prediction.

Reads raw operational drayage trip logs from PostgreSQL staging or raw CSV,
derives operational and temporal features, computes realistic ground-truth
travel times based on terminal kinematics and route congestion, and produces
the model-ready dataset.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import pandas as pd


# Default paths
RAW_CSV_DEFAULT = Path(
    r"D:\SLIIT\My\4th Yr 1st Sem (Jul-Nov_2026)\IT4010 - Research Project "
    r"(Comprehensive Design and Analysis Project)\Data Collecting\SmartPortData\truck_details.csv"
)
DATA_DIR = Path(__file__).resolve().parent / "data"
PREPARED_CSV_DEFAULT = DATA_DIR / "prepared_truck_trips.csv"

# Terminal physics and operational constants
SPEED_AGV_MPS = 5.0          # 18.0 km/h regulated AGV speed
SPEED_TRUCK_MPS = 6.11       # 22.0 km/h human-driven terminal tractor speed

ROUTE_CONGESTION_WEIGHTS = {
    "RT_ECT_MAIN": 0.25,
    "RT_JCT_YARD_01": 0.20,
    "RT_CICT_YARD_02": 0.15,
    "RT_INTERNAL_CORRIDOR_A": 0.10,
    "RT_SAGT_BYPASS": 0.05,
}

PEAK_HOURS = {8, 9, 10, 11, 14, 15, 16, 17}
NIGHT_HOURS = {22, 23, 0, 1, 2, 3, 4, 5}


def load_raw_dataset(csv_path: Optional[Path] = None, use_database: bool = False) -> pd.DataFrame:
    """
    Load raw truck trip logs from PostgreSQL staging table or local CSV.
    """
    if use_database:
        try:
            import psycopg
            from backend.drayage.config import get_settings
            settings = get_settings()
            conn = psycopg.connect(settings.database_url)
            query = "SELECT * FROM staging.truck_details;"
            df = pd.read_sql(query, conn)
            conn.close()
            # Normalize column names if coming from DB (lowercase)
            col_map = {
                "job_id": "Job_ID",
                "vessel_id": "Vessel_ID",
                "container_id": "Container_ID",
                "truck_id": "Truck_ID",
                "vehicle_type": "Vehicle_Type",
                "driver_id": "Driver_ID",
                "event_timestamp": "Timestamp",
                "start_zone": "Start_Zone",
                "destination_zone": "Destination_Zone",
                "distance_meters": "Distance_Meters",
                "route_id": "Route_ID",
            }
            df = df.rename(columns=col_map)
            print(f"[data_prep] Successfully loaded {len(df)} rows from PostgreSQL staging.truck_details")
            return df
        except Exception as e:
            print(f"[data_prep] Database load failed ({e}), falling back to CSV...")

    target_csv = csv_path or RAW_CSV_DEFAULT
    if not target_csv.exists():
        raise FileNotFoundError(f"Raw CSV not found at: {target_csv}")

    df = pd.read_csv(target_csv)
    print(f"[data_prep] Successfully loaded {len(df)} rows from CSV: {target_csv.name}")
    return df


def prepare_features(df: pd.DataFrame, random_seed: int = 42) -> pd.DataFrame:
    """
    Perform data cleaning, temporal extraction, terminal kinematics modeling,
    and compute ground-truth travel times.
    """
    data = df.copy()

    # Parse timestamps
    timestamps = pd.to_datetime(data["Timestamp"])
    data["departure_hour"] = timestamps.dt.hour
    data["day_of_week"] = timestamps.dt.day_of_week if hasattr(timestamps.dt, "day_of_week") else timestamps.dt.dayofweek
    data["is_peak_hour"] = data["departure_hour"].isin(PEAK_HOURS).astype(int)
    data["is_night_shift"] = data["departure_hour"].isin(NIGHT_HOURS).astype(int)

    # Route congestion factor
    route_factor = data["Route_ID"].map(ROUTE_CONGESTION_WEIGHTS).fillna(0.10)
    data["route_congestion_weight"] = route_factor

    # Vehicle cruising speed
    base_speed = np.where(data["Vehicle_Type"] == "AGV", SPEED_AGV_MPS, SPEED_TRUCK_MPS)
    data["base_speed_mps"] = base_speed

    # Combined traffic congestion multiplier
    congestion_multiplier = 1.0 + (route_factor * data["is_peak_hour"]) - (0.05 * data["is_night_shift"])
    data["congestion_multiplier"] = congestion_multiplier

    # Terminal maneuvering, crane queueing, and deceleration delays (seconds)
    np.random.seed(random_seed)
    maneuver_delay = np.random.uniform(35.0, 65.0, size=len(data))
    noise = np.random.normal(0, 4.0, size=len(data))

    # Formulate ground-truth travel times
    raw_travel_time_sec = (data["Distance_Meters"] / base_speed) * congestion_multiplier + maneuver_delay + noise
    data["travel_time_seconds"] = np.round(np.maximum(raw_travel_time_sec, 60.0), 2)
    data["travel_time_minutes"] = np.round(data["travel_time_seconds"] / 60.0, 3)

    return data


def save_prepared_dataset(df: pd.DataFrame, output_path: Optional[Path] = None) -> Path:
    """
    Save the engineered dataset to CSV for reproducible training.
    """
    out = output_path or PREPARED_CSV_DEFAULT
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"[data_prep] Saved prepared dataset ({len(df)} rows) to: {out}")
    return out


if __name__ == "__main__":
    raw_df = load_raw_dataset()
    prepared_df = prepare_features(raw_df)
    save_prepared_dataset(prepared_df)
    print("\nPrepared Dataset Summary:")
    print(prepared_df[["Distance_Meters", "Vehicle_Type", "Route_ID", "travel_time_seconds", "travel_time_minutes"]].describe())
