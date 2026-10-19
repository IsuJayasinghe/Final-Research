import math
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import joblib
import pandas as pd
import numpy as np

# Reference Port of Colombo coordinates (approximate terminal centroid)
PORT_COLOMBO_LAT = 6.9480
PORT_COLOMBO_LON = 79.8450
EARTH_RADIUS_NMI = 3440.065  # Nautical miles

def get_db_path() -> Path:
    current_file = Path(__file__).resolve()
    # Check Backend/smart_port.db
    backend_dir = current_file.parent.parent.parent
    db_path = backend_dir / "smart_port.db"
    if db_path.exists():
        return db_path
    # Fallback to local
    return Path("smart_port.db").resolve()

def get_eta_model_path() -> Path:
    current_file = Path(__file__).resolve()
    ml_path = current_file.parent / "eta_model.pkl"
    if ml_path.exists():
        return ml_path
    backend_path = current_file.parent.parent.parent / "eta_model.pkl"
    if backend_path.exists():
        return backend_path
    return ml_path

def get_delay_model_path() -> Path:
    current_file = Path(__file__).resolve()
    ml_path = current_file.parent / "delay_model.pkl"
    if ml_path.exists():
        return ml_path
    backend_path = current_file.parent.parent.parent / "delay_model.pkl"
    if backend_path.exists():
        return backend_path
    return ml_path

# Global caches for loaded models
_ETA_MODEL_CACHE: Optional[Dict[str, Any]] = None
_DELAY_MODEL_CACHE: Optional[Dict[str, Any]] = None

def load_eta_model() -> Dict[str, Any]:
    global _ETA_MODEL_CACHE
    if _ETA_MODEL_CACHE is not None:
        return _ETA_MODEL_CACHE

    model_path = get_eta_model_path()
    if not model_path.exists():
        raise FileNotFoundError(
            f"ETA Model file not found at {model_path}. "
            "Please run train_eta.py first to generate eta_model.pkl."
        )

    _ETA_MODEL_CACHE = joblib.load(model_path)
    return _ETA_MODEL_CACHE

def load_delay_model() -> Dict[str, Any]:
    global _DELAY_MODEL_CACHE
    if _DELAY_MODEL_CACHE is not None:
        return _DELAY_MODEL_CACHE

    model_path = get_delay_model_path()
    if not model_path.exists():
        raise FileNotFoundError(
            f"Delay Model file not found at {model_path}. "
            "Please run train_delay.py first to generate delay_model.pkl."
        )

    _DELAY_MODEL_CACHE = joblib.load(model_path)
    return _DELAY_MODEL_CACHE

def calculate_haversine_distance_nmi(
    lat1: float,
    lon1: float,
    lat2: float = PORT_COLOMBO_LAT,
    lon2: float = PORT_COLOMBO_LON
) -> float:
    """Calculate great-circle distance between two points in nautical miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(EARTH_RADIUS_NMI * c, 2)

def calculate_environmental_impact(
    wind_speed_knots: float,
    wave_height_m: float,
    draft_m: float,
    sog_knots: float,
    distance_to_port_nmi: float
) -> Dict[str, Any]:
    """
    Calculates hydrodynamic and sea-margin impact on vessel transit time.
    High winds (>12 kts) and rough waves (>1.2 m) degrade effective speed.
    """
    CALM_WIND_THRESHOLD = 12.0
    CALM_WAVE_THRESHOLD = 1.2

    excess_wind = max(0.0, wind_speed_knots - CALM_WIND_THRESHOLD)
    wind_penalty_rate = (excess_wind / 35.0) ** 1.3 * 0.22

    excess_wave = max(0.0, wave_height_m - CALM_WAVE_THRESHOLD)
    wave_penalty_rate = (excess_wave / 3.0) ** 1.4 * 0.32

    draft_factor = 1.0 + (max(0.0, draft_m - 10.0) / 10.0) * 0.15

    total_weather_penalty_pct = (wind_penalty_rate + wave_penalty_rate) * draft_factor
    total_weather_penalty_pct = min(total_weather_penalty_pct, 1.20)

    if wind_speed_knots >= 30.0 or wave_height_m >= 3.0:
        weather_condition = "Severe Storm Warning"
        risk_level = "High"
    elif wind_speed_knots >= 20.0 or wave_height_m >= 2.0:
        weather_condition = "Moderate Sea / Rough"
        risk_level = "Moderate"
    elif wind_speed_knots >= 14.0 or wave_height_m >= 1.4:
        weather_condition = "Slight Waves / Moderate Breeze"
        risk_level = "Low"
    else:
        weather_condition = "Calm / Favorable"
        risk_level = "Nominal"

    effective_speed_knots = max(2.0, sog_knots * (1.0 - (total_weather_penalty_pct * 0.4)))

    return {
        "weather_condition": weather_condition,
        "risk_level": risk_level,
        "wind_speed_knots": round(wind_speed_knots, 1),
        "wave_height_m": round(wave_height_m, 2),
        "weather_penalty_percent": round(total_weather_penalty_pct * 100, 1),
        "effective_speed_knots": round(effective_speed_knots, 2),
        "draft_factor": round(draft_factor, 2)
    }

def assess_delay_risk(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module 2: Evaluates vessel operational delay risk using the trained delay model
    and operational threshold rules (wind/wave spikes, speed drops, draft drag).
    Determines whether automated berth unbooking and reassignment should be triggered.
    """
    sog = float(telemetry.get("sog", telemetry.get("speed_knots", 14.0)))
    sog = max(1.0, sog)
    distance_to_port = float(telemetry.get("distance_to_port_nmi", 100.0))
    draft = float(telemetry.get("draft_m", 12.0))
    wind_speed = float(telemetry.get("wind_speed_knots", 15.0))
    wave_height = float(telemetry.get("wave_height_m", 1.5))

    # Feature engineering matching train_delay.py
    weather_severity = (wind_speed / 30.0) * (wave_height / 3.0)
    speed_drop_factor = max(0.0, 16.0 - sog) / 16.0
    hydrodynamic_drag = draft * (wave_height ** 1.3)

    delay_artifact = load_delay_model()
    clf = delay_artifact["classifier"]
    reg = delay_artifact.get("regressor")

    features_df = pd.DataFrame([{
        'sog': sog,
        'distance_to_port_nmi': distance_to_port,
        'draft_m': draft,
        'wind_speed_knots': wind_speed,
        'wave_height_m': wave_height,
        'weather_severity': weather_severity,
        'speed_drop_factor': speed_drop_factor,
        'hydrodynamic_drag': hydrodynamic_drag
    }])

    # Model inference
    delay_probability = float(clf.predict_proba(features_df)[0][1])
    predicted_delay_magnitude_hours = 0.0
    if reg is not None:
        predicted_delay_magnitude_hours = float(max(0.0, reg.predict(features_df)[0]))

    # Analyze physical delay triggers
    trigger_reasons = []
    if wind_speed >= 28.0:
        trigger_reasons.append(f"Severe wind spike ({wind_speed:.1f} kts exceeds 28 kts gale threshold)")
    elif wind_speed >= 20.0:
        trigger_reasons.append(f"Elevated wind resistance ({wind_speed:.1f} kts)")

    if wave_height >= 3.0:
        trigger_reasons.append(f"Extreme wave height ({wave_height:.1f}m creates heavy sea resistance)")
    elif wave_height >= 2.0:
        trigger_reasons.append(f"Rough sea state ({wave_height:.1f}m waves)")

    if sog <= 10.0:
        trigger_reasons.append(f"Critical speed drop ({sog:.1f} kts is well below cruising speed)")
    elif sog <= 13.0:
        trigger_reasons.append(f"Moderate speed reduction ({sog:.1f} kts)")

    if draft >= 14.5 and wave_height >= 2.0:
        trigger_reasons.append(f"Deep draft ({draft:.1f}m) compounding hydrodynamic drag in rough seas")

    # Determine risk level
    if delay_probability >= 0.80 or wind_speed >= 32.0 or wave_height >= 3.5:
        risk_level = "CRITICAL"
    elif delay_probability >= 0.65 or wind_speed >= 24.0 or wave_height >= 2.4 or sog <= 9.0:
        risk_level = "HIGH"
    elif delay_probability >= 0.40 or wind_speed >= 16.0 or wave_height >= 1.6:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    # Automation trigger flag
    trigger_reassignment = bool(
        risk_level in ["HIGH", "CRITICAL"]
        or delay_probability >= 0.65
        or (wind_speed >= 25.0 and wave_height >= 2.2)
        or sog <= 9.0
    )

    if trigger_reassignment and not trigger_reasons:
        trigger_reasons.append(f"Model classified schedule delay risk probability at {delay_probability*100:.1f}%")

    return {
        "delay_probability": round(delay_probability, 4),
        "delay_probability_percent": round(delay_probability * 100, 1),
        "predicted_delay_magnitude_hours": round(predicted_delay_magnitude_hours, 2),
        "risk_level": risk_level,
        "trigger_reassignment": trigger_reassignment,
        "trigger_reasons": trigger_reasons,
        "weather_severity_index": round(weather_severity, 3),
        "speed_drop_factor": round(speed_drop_factor, 3),
        "action_recommendation": (
            "Initiate immediate automated berth unbooking and reassignment."
            if trigger_reassignment else
            "Monitor vessel progression; schedule nominal."
        )
    }

def check_berth_constraints(draft_m: float) -> Dict[str, Any]:
    """Checks vessel draft against port berth constraints stored in smart_port.db."""
    db_path = get_db_path()
    if not db_path.exists():
        return {
            "suitable_berths_count": 0,
            "suitable_berths": [],
            "draft_warning": False,
            "message": "Database not initialized for berth check."
        }

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT berth_id, terminal_name, max_draft_m, max_length_m, crane_count
            FROM berth_characteristics
            ORDER BY max_draft_m DESC
        """)
        all_berths = cursor.fetchall()
        conn.close()

        suitable = []
        unsuitable = []
        for b in all_berths:
            berth_info = {
                "berth_id": b["berth_id"],
                "terminal_name": b["terminal_name"],
                "max_draft_m": b["max_draft_m"],
                "max_length_m": b["max_length_m"],
                "crane_count": b["crane_count"]
            }
            if b["max_draft_m"] >= draft_m:
                suitable.append(berth_info)
            else:
                unsuitable.append(berth_info)

        has_warning = len(suitable) == 0 or (draft_m > 15.0)
        warning_msg = None
        if len(suitable) == 0:
            warning_msg = f"Critical Alert: Vessel draft ({draft_m}m) exceeds all available berths in port!"
        elif draft_m > 14.5:
            warning_msg = f"Caution: Deep draft vessel ({draft_m}m) restricted to deep-water berths (e.g. CICT / SAGT)."

        return {
            "vessel_draft_m": round(draft_m, 2),
            "total_berths_in_port": len(all_berths),
            "suitable_berths_count": len(suitable),
            "suitable_berths": suitable[:5],
            "draft_warning": has_warning,
            "warning_message": warning_msg
        }
    except Exception as e:
        return {
            "vessel_draft_m": round(draft_m, 2),
            "error": str(e),
            "draft_warning": False
        }

def find_active_vessel_booking(vessel_imo: Optional[int]) -> Optional[Dict[str, Any]]:
    """Checks smart_port.db for an existing active 'BOOKED' reservation for this vessel IMO."""
    if not vessel_imo:
        return None
    db_path = get_db_path()
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT b.*, c.terminal_name, c.max_draft_m, c.max_length_m
            FROM berth_bookings b
            LEFT JOIN berth_characteristics c ON b.berth_id = c.berth_id
            WHERE b.vessel_imo = ? AND b.status = 'BOOKED'
            ORDER BY b.booking_id DESC LIMIT 1
        """, (vessel_imo,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None

def predict_vessel_eta(
    telemetry: Dict[str, Any],
    auto_trigger_reassignment: bool = False
) -> Dict[str, Any]:
    """
    Main prediction pipeline:
    1. Runs Module 1 (ETA regression model) for baseline transit hours.
    2. Runs hydrodynamic environmental impact calculation.
    3. Runs Module 2 (Delay Risk Classifier & Regressor) for delay probability and trigger detection.
    4. Evaluates against active berth bookings and triggers auto-reassignment if requested.
    """
    lat = float(telemetry.get("latitude", 0.0))
    lon = float(telemetry.get("longitude", 0.0))
    sog = float(telemetry.get("sog", telemetry.get("speed_knots", 14.0)))
    sog = max(1.0, sog)
    cog = float(telemetry.get("cog", telemetry.get("course", 0.0)))
    wind_speed = float(telemetry.get("wind_speed_knots", 10.0))
    wave_height = float(telemetry.get("wave_height_m", 1.0))
    draft = float(telemetry.get("draft_m", 10.0))
    vessel_imo = telemetry.get("imo_number")

    # Great-circle distance to port
    distance_to_port = telemetry.get("distance_to_port_nmi")
    if distance_to_port is None or float(distance_to_port) <= 0:
        distance_to_port = calculate_haversine_distance_nmi(lat, lon)
    else:
        distance_to_port = float(distance_to_port)

    # Reference timestamp
    raw_timestamp = telemetry.get("timestamp") or telemetry.get("base_datetime")
    if raw_timestamp:
        try:
            if "T" in str(raw_timestamp):
                base_time = datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
            else:
                base_time = datetime.strptime(str(raw_timestamp), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except Exception:
            base_time = datetime.now(timezone.utc)
    else:
        base_time = datetime.now(timezone.utc)

    # 1. Module 1: ETA Model Inference
    eta_artifact = load_eta_model()
    eta_model = eta_artifact["model"]
    features_df = pd.DataFrame([{
        'sog': sog,
        'distance_to_port_nmi': distance_to_port,
        'draft_m': draft,
        'wind_speed_knots': wind_speed,
        'wave_height_m': wave_height
    }])

    predicted_raw_hours = float(eta_model.predict(features_df)[0])
    predicted_raw_hours = max(0.5, predicted_raw_hours)

    # 2. Environmental Impact Dynamics
    env_impact = calculate_environmental_impact(
        wind_speed_knots=wind_speed,
        wave_height_m=wave_height,
        draft_m=draft,
        sog_knots=sog,
        distance_to_port_nmi=distance_to_port
    )

    penalty_ratio = env_impact["weather_penalty_percent"] / 100.0
    weather_delay_hours = predicted_raw_hours * penalty_ratio
    dynamic_remaining_hours = predicted_raw_hours + weather_delay_hours

    baseline_arrival_dt = base_time + timedelta(hours=predicted_raw_hours)
    dynamic_arrival_dt = base_time + timedelta(hours=dynamic_remaining_hours)

    # 3. Module 2: Delay Risk Assessment
    telemetry_augmented = dict(telemetry)
    telemetry_augmented["distance_to_port_nmi"] = distance_to_port
    delay_risk = assess_delay_risk(telemetry_augmented)
    delay_artifact = load_delay_model()

    # 4. Berth Constraints Evaluation
    berth_evaluation = check_berth_constraints(draft)

    # 5. Active Booking Evaluation & Automated Reassignment Trigger
    active_booking = find_active_vessel_booking(vessel_imo)
    schedule_status = {
        "has_active_booking": active_booking is not None,
        "booking_id": active_booking["booking_id"] if active_booking else None,
        "booked_berth_id": active_booking["berth_id"] if active_booking else None,
        "booked_start_time": active_booking["start_time"] if active_booking else None,
        "booked_end_time": active_booking["end_time"] if active_booking else None,
        "schedule_violation": False,
        "schedule_advisory": "Nominal"
    }

    reassignment_execution = None

    if active_booking:
        try:
            booked_start = datetime.fromisoformat(active_booking["start_time"].replace("Z", "+00:00"))
            booked_end = datetime.fromisoformat(active_booking["end_time"].replace("Z", "+00:00"))

            is_delayed_overrun = dynamic_arrival_dt > booked_start
            is_slot_expiration_conflict = (dynamic_arrival_dt + timedelta(hours=3.0)) > booked_end
            is_risk_triggered = delay_risk.get("trigger_reassignment", False)

            if is_delayed_overrun or is_slot_expiration_conflict or is_risk_triggered:
                schedule_status["schedule_violation"] = True
                overrun_hours = max(0.0, (dynamic_arrival_dt - booked_start).total_seconds() / 3600.0)
                schedule_status["delay_overrun_hours"] = round(overrun_hours, 2)

                reasons = []
                if is_delayed_overrun:
                    reasons.append(f"Dynamic ETA ({dynamic_arrival_dt.strftime('%Y-%m-%d %H:%M')} UTC) drifts {overrun_hours:.1f} hrs past booked start window.")
                if is_slot_expiration_conflict and not is_delayed_overrun:
                    reasons.append(f"Vessel arrival window cannot complete cargo operations prior to slot expiration at {booked_end.strftime('%Y-%m-%d %H:%M')} UTC.")
                if is_risk_triggered:
                    reasons.append(f"Delay risk classified as {delay_risk.get('risk_level', 'HIGH')} due to severe meteo-oceanographic factors.")

                schedule_status["schedule_advisory"] = " | ".join(reasons)

                if auto_trigger_reassignment or is_risk_triggered:
                    # Invoke event-driven dynamic berth unbooking & reallocation
                    try:
                        from app.berth_allocator import cancel_and_reassign_berth
                    except ImportError:
                        from berth_allocator import cancel_and_reassign_berth

                    reassignment_execution = cancel_and_reassign_berth(
                        booking_id=active_booking["booking_id"],
                        new_eta=dynamic_arrival_dt.isoformat(),
                        duration_hours=None,
                        auto_reassign=True,
                        length_m=float(telemetry.get("length_m", 300.0)),
                        draft_m=draft
                    )
                    schedule_status["automated_reassignment_triggered"] = True
                    schedule_status["new_berth_assigned"] = reassignment_execution.get("new_booking", {}).get("berth_id") if reassignment_execution else None
        except Exception as e:
            schedule_status["error"] = str(e)


    return {
        "vessel_info": {
            "mmsi": telemetry.get("mmsi"),
            "imo_number": vessel_imo,
            "vessel_name": telemetry.get("vessel_name", "Unknown Vessel"),
            "vessel_type": telemetry.get("vessel_type", "Cargo/Container"),
            "latitude": lat,
            "longitude": lon,
            "sog_knots": sog,
            "cog_degrees": cog,
            "draft_m": draft,
            "distance_to_port_nmi": distance_to_port
        },
        "eta_prediction": {
            "base_timestamp": base_time.isoformat(),
            "baseline_remaining_hours": round(predicted_raw_hours, 2),
            "weather_delay_hours": round(weather_delay_hours, 2),
            "dynamic_remaining_hours": round(dynamic_remaining_hours, 2),
            "baseline_eta": baseline_arrival_dt.isoformat(),
            "dynamic_eta": dynamic_arrival_dt.isoformat()
        },
        "environmental_impact": env_impact,
        "delay_risk_assessment": delay_risk,
        "berth_constraints": berth_evaluation,
        "schedule_status": schedule_status,
        "automated_reassignment": reassignment_execution,
        "model_metadata": {
            "eta_model": {
                "type": eta_artifact.get("metadata", {}).get("model_type", "RandomForestRegressor"),
                "mae_hours": eta_artifact.get("metrics", {}).get("mae", 12.3)
            },
            "delay_model": {
                "type": delay_artifact.get("metadata", {}).get("model_type", "RandomForestClassifier"),
                "f1_score": delay_artifact.get("metrics", {}).get("f1", 0.69),
                "roc_auc": delay_artifact.get("metrics", {}).get("roc_auc", 0.78)
            }
        }
    }
