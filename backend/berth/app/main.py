from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from app.ml.prediction import predict_vessel_eta, assess_delay_risk, get_db_path
    from app.berth_allocator import (
        get_available_berths,
        book_berth,
        cancel_and_reassign_berth,
        get_all_bookings,
        ensure_berth_bookings_table,
        release_berth_booking
    )
except ImportError:
    from ml.prediction import predict_vessel_eta, assess_delay_risk, get_db_path
    from berth_allocator import (
        get_available_berths,
        book_berth,
        cancel_and_reassign_berth,
        get_all_bookings,
        ensure_berth_bookings_table,
        release_berth_booking
    )

app = FastAPI(
    title="Smart Port Management System - Component 1 API",
    description="Real-time Vessel Telemetry, Dynamic ETA Prediction, Delay Risk Assessment & Automated Berth Scheduling API",
    version="1.2.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """Ensure database tables exist on server startup."""
    db_path = get_db_path()
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        ensure_berth_bookings_table(conn)
        conn.close()

# --- Pydantic Request & Response Schemas ---

class VesselTelemetryRequest(BaseModel):
    mmsi: Optional[int] = Field(None, description="Maritime Mobile Service Identity")
    imo_number: Optional[int] = Field(None, description="International Maritime Organization number")
    vessel_name: Optional[str] = Field("Unknown Vessel", description="Vessel name")
    vessel_type: Optional[str] = Field("Container Ship", description="Type of vessel")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Current latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Current longitude")
    sog: float = Field(..., ge=0.0, description="Speed Over Ground (knots)")
    cog: Optional[float] = Field(0.0, ge=0.0, le=360.0, description="Course Over Ground (degrees)")
    timestamp: Optional[str] = Field(None, description="ISO timestamp or datetime string")
    wind_speed_knots: float = Field(..., ge=0.0, description="Ambient wind speed (knots)")
    wave_height_m: float = Field(..., ge=0.0, description="Significant wave height (meters)")
    draft_m: float = Field(..., gt=0.0, description="Vessel current draft (meters)")
    length_m: Optional[float] = Field(300.0, gt=0.0, description="Vessel overall length in meters (default 300.0)")
    distance_to_port_nmi: Optional[float] = Field(None, ge=0.0, description="Distance to port (nmi). Auto-computed if omitted.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "mmsi": 409321483,
                "imo_number": 9321483,
                "vessel_name": "EMMA MAERSK",
                "vessel_type": "Container Ship",
                "latitude": 6.6878,
                "longitude": 79.6253,
                "sog": 18.6,
                "cog": 195.4,
                "wind_speed_knots": 24.5,
                "wave_height_m": 2.8,
                "draft_m": 14.9,
                "length_m": 397.0,
                "timestamp": "2026-10-19T08:00:00Z"
            }
        }
    }


class BerthInfo(BaseModel):
    berth_id: str
    terminal_name: str
    max_draft_m: float
    max_length_m: float
    crane_count: int

class BerthEvaluation(BaseModel):
    vessel_draft_m: float
    total_berths_in_port: int
    suitable_berths_count: int
    suitable_berths: List[Dict[str, Any]]
    draft_warning: bool
    warning_message: Optional[str] = None

class EnvironmentalImpact(BaseModel):
    weather_condition: str
    risk_level: str
    wind_speed_knots: float
    wave_height_m: float
    weather_penalty_percent: float
    effective_speed_knots: float
    draft_factor: float

class DelayRiskAssessment(BaseModel):
    delay_probability: float
    delay_probability_percent: float
    predicted_delay_magnitude_hours: float
    risk_level: str
    trigger_reassignment: bool
    trigger_reasons: List[str]
    weather_severity_index: float
    speed_drop_factor: float
    action_recommendation: str

class EtaPredictionDetails(BaseModel):
    base_timestamp: str
    baseline_remaining_hours: float
    weather_delay_hours: float
    dynamic_remaining_hours: float
    baseline_eta: str
    dynamic_eta: str

class DynamicEtaResponse(BaseModel):
    status: str
    vessel_info: Dict[str, Any]
    eta_prediction: EtaPredictionDetails
    environmental_impact: EnvironmentalImpact
    delay_risk_assessment: DelayRiskAssessment
    berth_constraints: BerthEvaluation
    schedule_status: Optional[Dict[str, Any]] = None
    automated_reassignment: Optional[Dict[str, Any]] = None
    model_metadata: Dict[str, Any]

class BookBerthRequest(BaseModel):
    vessel_imo: int = Field(..., description="IMO Number of the vessel")
    vessel_name: str = Field(..., description="Name of the vessel")
    berth_id: str = Field(..., description="Target Berth Identifier (e.g., JCT_01)")
    start_time: str = Field(..., description="Booking start timestamp (ISO-8601)")
    end_time: str = Field(..., description="Booking end timestamp (ISO-8601)")
    length_m: Optional[float] = Field(None, gt=0.0, description="Vessel length in meters (optional validation)")
    draft_m: Optional[float] = Field(None, gt=0.0, description="Vessel draft in meters (optional validation)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "vessel_imo": 9321483,
                "vessel_name": "EMMA MAERSK",
                "berth_id": "CICT_01",
                "start_time": "2026-10-19T14:00:00Z",
                "end_time": "2026-10-20T02:00:00Z",
                "length_m": 397.0,
                "draft_m": 15.5
            }
        }
    }

class CancelReassignRequest(BaseModel):
    booking_id: Optional[int] = Field(None, description="Booking ID to cancel and reassign")
    vessel_imo: Optional[int] = Field(None, description="Vessel IMO (if booking_id not provided)")
    new_eta: str = Field(..., description="New dynamic ETA timestamp (ISO-8601)")
    duration_hours: Optional[float] = Field(None, gt=0.0, description="Duration in hours for the new booking window")
    auto_reassign: bool = Field(True, description="Automatically book the best available alternative berth")
    length_m: Optional[float] = Field(300.0, gt=0.0, description="Vessel length in meters")
    draft_m: Optional[float] = Field(12.0, gt=0.0, description="Vessel draft in meters")

    model_config = {
        "json_schema_extra": {
            "example": {
                "vessel_imo": 9321483,
                "new_eta": "2026-10-19T22:00:00Z",
                "duration_hours": 12.0,
                "auto_reassign": True,
                "length_m": 397.0,
                "draft_m": 15.5
            }
        }
    }

# --- Core API Endpoints ---

@app.get("/")
def root():
    return {
        "system": "Smart Port Management System - Component 1",
        "description": "Real-time Telemetry, Dynamic ETA Prediction, Delay Risk Assessment & Automated Berth Scheduling API",
        "status": "online",
        "endpoints": {
            "predict_eta": "POST /api/vessels/predict-eta?auto_trigger_reassignment=false",
            "assess_delay_risk": "POST /api/vessels/assess-delay-risk",
            "available_berths": "GET /api/berths/available?length_m=300&draft_m=13&start_time=...&end_time=...",
            "book_berth": "POST /api/berths/book",
            "cancel_reassign": "POST /api/berths/cancel-reassign",
            "release_berth": "POST /api/berths/{berth_id}/release",
            "cancel_booking": "DELETE /api/berths/bookings/{booking_id}",
            "bookings": "GET /api/berths/bookings",
            "berths_list": "GET /api/berths",
            "berth_matrix": "GET /api/berths/matrix",
            "berth_detail": "GET /api/berths/{berth_id}",
            "sample_telemetry": "GET /api/vessels/sample",
            "incoming_vessels": "GET /api/vessels",
            "health": "GET /api/health",
            "docs": "/docs"
        }
    }

VESSEL_SPECIFIC_LENGTHS = {
    9321483: 397.0,   # EMMA MAERSK
    8420804: 342.0,   # BERGE STAHL
    9690121: 292.0,   # VALIANT
    9839179: 400.0,   # CMA CGM JACQUES SAADE
    9776171: 399.9,   # OOCL HONG KONG
    9811000: 399.9,   # EVER GIVEN
    9839430: 399.9,   # MSC GÜLSÜN
    9863297: 399.9,   # HMM ALGECIRAS
    9769271: 400.0,   # MOL TRIUMPH
    9795610: 400.0,   # COSCO SHIPPING UNIVERSE
    9619907: 399.0,   # MAERSK MC-KINNEY MØLLER
    9708679: 395.4,   # MSC MAYA
    9488918: 362.0,   # ORE BRASIL / VALE BRASIL
    9224752: 380.0,   # TI EUROPE
    9775656: 183.0,   # STENA IMPERO
    9168647: 182.7,   # STOLT COMMITMENT
    9328951: 243.8,   # EAGLE S
    9418063: 333.0,   # NISSOS RHENIA
    9218124: 240.0,   # JOLLY TITANIO
    9274168: 180.0,   # PACIFIC BASIN
    9469362: 143.0,   # BBC EUROPE
    9506102: 143.0,   # BBC MARMARA
    9506097: 143.0,   # BBC STEINWALL
    9506126: 143.0,   # BBC CAMPANA
    9451224: 130.0,   # GENERAL ROMEO
    9454100: 132.0,   # BELUGA NOMINATION
    9290050: 140.0,   # THORCO CLOUD
    9397531: 140.0,   # THORCO ANGEL
    1052191: 120.0,   # WILSON ECO VI
}

TYPE_DEFAULT_LENGTHS = {
    'Container Ship': 350.0,
    'Bulk Carrier': 280.0,
    'Oil Tanker': 260.0,
    'Oil/Chemical Tanker': 220.0,
    'General Cargo Ship': 160.0
}

DEFAULT_INCOMING_VESSELS = [
    {
        "mmsi": 409321483,
        "imo_number": 9321483,
        "vessel_name": "EMMA MAERSK",
        "vessel_type": "Container Ship",
        "latitude": 6.6878,
        "longitude": 79.6253,
        "sog": 18.6,
        "cog": 195.4,
        "distance_to_port_nmi": 22.4,
        "draft_m": 14.9,
        "length_m": 397.0,
        "wind_speed_knots": 24.5,
        "wave_height_m": 2.8,
    },
    {
        "mmsi": 408420804,
        "imo_number": 8420804,
        "vessel_name": "BERGE STAHL",
        "vessel_type": "Bulk Carrier",
        "latitude": 6.9784,
        "longitude": 80.0077,
        "sog": 17.5,
        "cog": 177.8,
        "distance_to_port_nmi": 14.8,
        "draft_m": 12.8,
        "length_m": 342.0,
        "wind_speed_knots": 14.2,
        "wave_height_m": 1.2,
    },
    {
        "mmsi": 409690121,
        "imo_number": 9690121,
        "vessel_name": "VALIANT",
        "vessel_type": "Bulk Carrier",
        "latitude": 6.1179,
        "longitude": 79.4989,
        "sog": 9.8,
        "cog": 305.1,
        "distance_to_port_nmi": 58.2,
        "draft_m": 13.5,
        "length_m": 292.0,
        "wind_speed_knots": 29.4,
        "wave_height_m": 3.2,
    },
    {
        "mmsi": 409839179,
        "imo_number": 9839179,
        "vessel_name": "CMA CGM JACQUES SAADE",
        "vessel_type": "Container Ship",
        "latitude": 6.8200,
        "longitude": 79.7100,
        "sog": 19.2,
        "cog": 210.0,
        "distance_to_port_nmi": 11.5,
        "draft_m": 15.6,
        "length_m": 400.0,
        "wind_speed_knots": 18.0,
        "wave_height_m": 1.8,
    },
    {
        "mmsi": 409776171,
        "imo_number": 9776171,
        "vessel_name": "OOCL HONG KONG",
        "vessel_type": "Container Ship",
        "latitude": 7.2100,
        "longitude": 79.5500,
        "sog": 16.4,
        "cog": 160.0,
        "distance_to_port_nmi": 32.0,
        "draft_m": 14.2,
        "length_m": 399.9,
        "wind_speed_knots": 11.0,
        "wave_height_m": 0.9,
    }
]

@app.get("/api/vessels")
@app.get("/api/vessels/incoming")
def list_incoming_vessels():
    """
    Returns the list of incoming vessels approaching Port of Colombo
    from vessel telemetry and historical records in smart_port.db.
    Includes IMO, name, type, draft, length, coordinates, and ETA metrics.
    """
    db_path = get_db_path()
    if not db_path.exists():
        return {
            "status": "success",
            "source": "fallback",
            "total_vessels": len(DEFAULT_INCOMING_VESSELS),
            "vessels": DEFAULT_INCOMING_VESSELS
        }

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query latest telemetry record per unique vessel IMO
        cursor.execute("""
            SELECT v1.*
            FROM vessel_historical_data v1
            INNER JOIN (
                SELECT imo_number, MAX(id) as max_id
                FROM vessel_historical_data
                GROUP BY imo_number
            ) v2 ON v1.id = v2.max_id
            ORDER BY v1.vessel_name ASC
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "status": "success",
                "source": "fallback",
                "total_vessels": len(DEFAULT_INCOMING_VESSELS),
                "vessels": DEFAULT_INCOMING_VESSELS
            }

        vessels = []
        for r in rows:
            row_dict = dict(r)
            imo = row_dict.get("imo_number")
            v_name = row_dict.get("vessel_name") or "Unknown Vessel"
            v_type = row_dict.get("vessel_type") or "Container Ship"
            length_m = VESSEL_SPECIFIC_LENGTHS.get(imo, TYPE_DEFAULT_LENGTHS.get(v_type, 280.0))
            raw_draft = row_dict.get("draft_m")
            draft_m = round(float(raw_draft), 1) if raw_draft is not None else 12.0

            vessels.append({
                "imo_number": imo,
                "vessel_name": v_name,
                "vessel_type": v_type,
                "length_m": length_m,
                "draft_m": draft_m,
                "mmsi": row_dict.get("mmsi"),
                "distance_to_port_nmi": round(float(row_dict.get("distance_to_port_nmi") or 0.0), 1),
                "sog": round(float(row_dict.get("sog") or 0.0), 1),
                "cog": round(float(row_dict.get("cog") or 0.0), 1),
                "wind_speed_knots": round(float(row_dict.get("wind_speed_knots") or 0.0), 1),
                "wave_height_m": round(float(row_dict.get("wave_height_m") or 0.0), 1),
                "latitude": row_dict.get("latitude"),
                "longitude": row_dict.get("longitude")
            })

        return {
            "status": "success",
            "source": "database",
            "total_vessels": len(vessels),
            "vessels": vessels
        }
    except Exception as e:
        return {
            "status": "partial_success",
            "source": "fallback_on_error",
            "error": str(e),
            "total_vessels": len(DEFAULT_INCOMING_VESSELS),
            "vessels": DEFAULT_INCOMING_VESSELS
        }

@app.get("/api/health")
def health_check():
    db_path = get_db_path()
    db_available = db_path.exists()
    return {
        "status": "healthy",
        "database_connected": db_available,
        "database_path": str(db_path),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/vessels/sample")
def get_sample_telemetry():
    """Returns sample vessel telemetry data ready to test with."""
    return {
        "mmsi": 409321483,
        "imo_number": 9321483,
        "vessel_name": "EMMA MAERSK",
        "vessel_type": "Container Ship",
        "latitude": 6.6878,
        "longitude": 79.6253,
        "sog": 18.6,
        "cog": 195.4,
        "wind_speed_knots": 25.0,
        "wave_height_m": 2.7,
        "draft_m": 14.9,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/berths")
def list_berths():
    """Returns list of berths and their operational constraints from SQLite."""
    db_path = get_db_path()
    if not db_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database smart_port.db not found. Run init_db.py first."
        )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT instance_id, terminal_name, berth_id, max_length_m, max_draft_m, crane_count, crane_handling_rate_teu_hr
        FROM berth_characteristics
        ORDER BY terminal_name, berth_id
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {
        "total_berths": len(rows),
        "berths": rows
    }

@app.get("/api/berths/matrix")
def get_berth_matrix():
    """
    Returns an aggregated berth occupancy matrix grouped by terminal.
    Optimized for React frontend dashboard grids and timeline visualizers.
    """
    db_path = get_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not found.")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT instance_id, terminal_name, berth_id, max_length_m, max_draft_m, crane_count, crane_handling_rate_teu_hr
        FROM berth_characteristics
        ORDER BY terminal_name, berth_id
    """)
    berths = [dict(row) for row in cursor.fetchall()]

    # Fetch active reservations
    cursor.execute("""
        SELECT booking_id, vessel_imo, vessel_name, berth_id, start_time, end_time, status
        FROM berth_bookings
        WHERE status = 'BOOKED'
        ORDER BY start_time ASC
    """)
    active_bookings = [dict(row) for row in cursor.fetchall()]
    conn.close()

    now_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Map bookings to berths
    berth_bookings_map: Dict[str, List[Dict[str, Any]]] = {}
    for b in active_bookings:
        berth_bookings_map.setdefault(b["berth_id"], []).append(b)

    terminals: Dict[str, List[Dict[str, Any]]] = {}
    total_occupied = 0

    for b in berths:
        t_name = b["terminal_name"]
        b_id = b["berth_id"]
        b_bookings = berth_bookings_map.get(b_id, [])

        # Check if currently occupied
        current_occ = None
        for bk in b_bookings:
            if bk["start_time"] <= now_utc_str <= bk["end_time"]:
                current_occ = bk
                break
        if not current_occ and b_bookings:
            # If no booking exactly right now, point to earliest upcoming
            current_occ = b_bookings[0]

        is_occupied = (current_occ is not None)
        if is_occupied:
            total_occupied += 1

        berth_payload = {
            **b,
            "is_occupied": is_occupied,
            "current_booking": current_occ,
            "upcoming_bookings_count": len(b_bookings),
            "upcoming_bookings": b_bookings[:3]
        }
        terminals.setdefault(t_name, []).append(berth_payload)

    return {
        "status": "success",
        "timestamp": now_utc_str,
        "total_berths": len(berths),
        "total_occupied_slots": total_occupied,
        "total_terminals": len(terminals),
        "terminal_matrix": terminals
    }

@app.get("/api/berths/{berth_id}")
def get_berth_detail(berth_id: str):
    """Returns detailed characteristics and reservation history for a specific berth."""
    db_path = get_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not found.")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT instance_id, terminal_name, berth_id, max_length_m, max_draft_m, crane_count, crane_handling_rate_teu_hr
        FROM berth_characteristics
        WHERE berth_id = ?
    """, (berth_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Berth '{berth_id}' not found in port database."
        )

    berth_info = dict(row)

    cursor.execute("""
        SELECT booking_id, vessel_imo, vessel_name, berth_id, start_time, end_time, status
        FROM berth_bookings
        WHERE berth_id = ?
        ORDER BY start_time ASC
    """, (berth_id,))
    bookings = [dict(b) for b in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "berth": berth_info,
        "total_bookings": len(bookings),
        "bookings": bookings
    }


@app.post("/api/vessels/predict-eta", response_model=DynamicEtaResponse)
def predict_eta(
    payload: VesselTelemetryRequest,
    auto_trigger_reassignment: bool = Query(
        False,
        description="Automatically trigger berth cancellation and reassignment if delay causes schedule overrun"
    )
):
    """
    Module 1 & 2 Integrated Endpoint:
    Accepts live JSON vessel telemetry payloads, computes environmental delays,
    runs the ML ETA model, evaluates operational delay risk, checks port/berth constraints,
    and returns real-time dynamic ETA with schedule advisory and optional automated reassignment.
    """
    try:
        telemetry_dict = payload.model_dump()
        result = predict_vessel_eta(
            telemetry_dict,
            auto_trigger_reassignment=auto_trigger_reassignment
        )
        return {
            "status": "success",
            **result
        }
    except FileNotFoundError as fnf:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(fnf)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing dynamic ETA prediction: {str(e)}"
        )

@app.post("/api/vessels/assess-delay-risk")
def assess_delay_risk_endpoint(payload: VesselTelemetryRequest):
    """
    Module 2 Standalone Endpoint:
    Evaluates delay probability, magnitude, risk category (LOW/MODERATE/HIGH/CRITICAL),
    and whether automated berth reassignment should be triggered.
    """
    try:
        telemetry_dict = payload.model_dump()
        risk_result = assess_delay_risk(telemetry_dict)
        return {
            "status": "success",
            "vessel_name": payload.vessel_name,
            "imo_number": payload.imo_number,
            **risk_result
        }
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Berth Scheduling, Matching & Dynamic Reassignment Endpoints ---

@app.get("/api/berths/available")
def get_available_berths_endpoint(
    length_m: float = Query(..., gt=0.0, description="Vessel overall length in meters"),
    draft_m: float = Query(..., gt=0.0, description="Vessel draft in meters"),
    start_time: str = Query(..., description="Requested start timestamp (ISO-8601, e.g., 2026-10-19T14:00:00Z)"),
    end_time: str = Query(..., description="Requested end timestamp (ISO-8601, e.g., 2026-10-20T02:00:00Z)"),
    terminal_name: Optional[str] = Query(None, description="Optional terminal name filter (e.g. JCT, CICT, SAGT)")
):
    """
    Query all berths that:
    1. Physically accommodate the vessel (length <= max_length_m and draft <= max_draft_m).
    2. Have no conflicting 'BOOKED' reservation during the requested [start_time, end_time] window.
    """
    try:
        available = get_available_berths(
            length_m=length_m,
            draft_m=draft_m,
            start_time=start_time,
            end_time=end_time,
            terminal_name=terminal_name
        )
        return {
            "status": "success",
            "requested_window": {
                "start_time": start_time,
                "end_time": end_time
            },
            "vessel_criteria": {
                "length_m": length_m,
                "draft_m": draft_m,
                "terminal_filter": terminal_name
            },
            "total_available": len(available),
            "available_berths": available
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/api/berths/book", status_code=status.HTTP_201_CREATED)
def book_berth_endpoint(payload: BookBerthRequest):
    """
    Creates a new berth booking record.
    Ensures vessel fits the berth and prevents double-booking overlaps.
    """
    try:
        booking = book_berth(
            vessel_imo=payload.vessel_imo,
            vessel_name=payload.vessel_name,
            berth_id=payload.berth_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            length_m=payload.length_m,
            draft_m=payload.draft_m
        )
        return {
            "status": "success",
            "message": f"Berth {payload.berth_id} successfully booked for '{payload.vessel_name}'.",
            "booking": booking
        }
    except ValueError as ve:
        err_msg = str(ve)
        if "Validation Error: Vessel" in err_msg or "conflicting berth reservation" in err_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
        if "Double-booking conflict" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/api/berths/cancel-reassign")
def cancel_and_reassign_endpoint(payload: CancelReassignRequest):
    """
    Handles vessel delays (e.g. from worsening wind/waves).
    Updates delayed vessel's booking to 'CANCELLED_AND_REASSIGNED', frees up the old slot,
    and searches for / assigns the next available compatible berth for the updated ETA.
    """
    try:
        result = cancel_and_reassign_berth(
            booking_id=payload.booking_id,
            vessel_imo=payload.vessel_imo,
            new_eta=payload.new_eta,
            duration_hours=payload.duration_hours,
            auto_reassign=payload.auto_reassign,
            length_m=payload.length_m,
            draft_m=payload.draft_m
        )
        return result
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/berths/bookings")
def list_bookings_endpoint(
    status: Optional[str] = Query(None, description="Filter by status: BOOKED, COMPLETED, CANCELLED_AND_REASSIGNED"),
    berth_id: Optional[str] = Query(None, description="Filter by berth ID")
):
    """
    Lists current active and historical berth allocations/bookings for port schedule visualization.
    """
    try:
        bookings = get_all_bookings(status=status, berth_id=berth_id)
        return {
            "status": "success",
            "total_bookings": len(bookings),
            "filters": {
                "status": status,
                "berth_id": berth_id
            },
            "bookings": bookings
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.delete("/api/berths/bookings/{booking_id}")
@app.post("/api/berths/bookings/{booking_id}/release")
def cancel_booking_endpoint(booking_id: int):
    """
    Releases an active booking record from berth_bookings,
    setting its status to 'RELEASED' and returning the berth back to free/available.
    """
    try:
        result = release_berth_booking(booking_id=booking_id)
        return result
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/api/berths/{berth_id}/release")
def release_berth_endpoint(
    berth_id: str,
    booking_id: Optional[int] = Query(None, description="Optional booking ID to release")
):
    """
    Releases the active booking on the specified berth ID,
    updating the berth back to free/available.
    """
    try:
        result = release_berth_booking(booking_id=booking_id, berth_id=berth_id)
        return result
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
