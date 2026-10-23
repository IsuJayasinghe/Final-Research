"""
Inference Engine and Travel Time Predictor for Component 2 Drayage System.

Loads the trained XGBoost model pipeline and exposes high-performance
prediction methods for single trips and batch assignments.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "models" / "travel_time_xgb.joblib"
METRICS_PATH = Path(__file__).resolve().parent / "models" / "model_metrics.json"

PEAK_HOURS = {8, 9, 10, 11, 14, 15, 16, 17}
NIGHT_HOURS = {22, 23, 0, 1, 2, 3, 4, 5}


class TravelTimePredictor:
    """Singleton-friendly predictor wrapping the trained XGBoost pipeline."""

    _instance: Optional["TravelTimePredictor"] = None
    _pipeline = None

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH
        self._load_pipeline()

    def _load_pipeline(self):
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Trained model not found at {self.model_path}. "
                "Please run 'python -m backend.drayage.ml.train' first."
            )
        self._pipeline = joblib.load(self.model_path)

    @classmethod
    def get_instance(cls) -> "TravelTimePredictor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def predict_trip(
        self,
        distance_meters: float,
        vehicle_type: str = "Internal_Drayage_Truck",
        route_id: str = "RT_ECT_MAIN",
        start_zone: str = "CICT_Berth_01",
        destination_zone: str = "Yard_Block_A",
        departure_hour: Optional[int] = None,
        day_of_week: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Predict travel duration for a single trip.
        """
        now = datetime.now()
        dep_hour = departure_hour if departure_hour is not None else now.hour
        dow = day_of_week if day_of_week is not None else now.weekday()

        is_peak = int(dep_hour in PEAK_HOURS)
        is_night = int(dep_hour in NIGHT_HOURS)

        row = {
            "Distance_Meters": float(distance_meters),
            "Vehicle_Type": str(vehicle_type),
            "Route_ID": str(route_id),
            "Start_Zone": str(start_zone),
            "Destination_Zone": str(destination_zone),
            "departure_hour": int(dep_hour),
            "day_of_week": int(dow),
            "is_peak_hour": is_peak,
            "is_night_shift": is_night,
        }

        df_in = pd.DataFrame([row])
        pred_sec = float(self._pipeline.predict(df_in)[0])
        pred_sec = max(pred_sec, 60.0)  # Terminal safety floor: 1 minute
        pred_min = round(pred_sec / 60.0, 2)

        return {
            "predicted_travel_time_seconds": round(pred_sec, 1),
            "predicted_travel_time_minutes": pred_min,
            "distance_meters": distance_meters,
            "vehicle_type": vehicle_type,
            "route_id": route_id,
            "start_zone": start_zone,
            "destination_zone": destination_zone,
            "departure_hour": dep_hour,
            "is_peak_hour": bool(is_peak),
            "is_night_shift": bool(is_night),
        }

    def predict_batch(self, trips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Vectorized batch prediction for multiple candidate assignments.
        """
        if not trips:
            return []

        now = datetime.now()
        cur_hour = now.hour
        cur_dow = now.weekday()

        rows = []
        for t in trips:
            dep_hour = t.get("departure_hour", cur_hour)
            dow = t.get("day_of_week", cur_dow)
            is_peak = int(dep_hour in PEAK_HOURS)
            is_night = int(dep_hour in NIGHT_HOURS)

            rows.append({
                "Distance_Meters": float(t["distance_meters"]),
                "Vehicle_Type": str(t.get("vehicle_type", "Internal_Drayage_Truck")),
                "Route_ID": str(t.get("route_id", "RT_ECT_MAIN")),
                "Start_Zone": str(t.get("start_zone", "CICT_Berth_01")),
                "Destination_Zone": str(t.get("destination_zone", "Yard_Block_A")),
                "departure_hour": int(dep_hour),
                "day_of_week": int(dow),
                "is_peak_hour": is_peak,
                "is_night_shift": is_night,
            })

        df_in = pd.DataFrame(rows)
        preds = self._pipeline.predict(df_in)

        results = []
        for i, pred_sec in enumerate(preds):
            sec = max(float(pred_sec), 60.0)
            res = dict(trips[i])
            res["predicted_travel_time_seconds"] = round(sec, 1)
            res["predicted_travel_time_minutes"] = round(sec / 60.0, 2)
            results.append(res)

        return results
