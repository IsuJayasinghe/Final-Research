"""Component 4 (Gate Appointment) API routes.

Kept as an APIRouter so the shared backend can mount it later with
`app.include_router(gate_router)`; main.py runs it standalone for now.
"""

from datetime import datetime, timedelta

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

import documents
import ml_models
import noshow
import service
import templates
import vessels
import weather
from schemas import (
    AppointmentRequest,
    AppointmentResponse,
    BookingRequest,
    ClearanceRequest,
    ClearanceResponse,
    CongestionResponse,
    DisruptionRequest,
    LaneCongestion,
    ModelInputs,
)

router = APIRouter(prefix="/api")


def _arrival_datetime(inputs: ModelInputs) -> datetime:
    """Planned gate arrival from the user's date + hour, defaulting to now."""
    now = datetime.now()
    try:
        base = datetime.strptime(inputs.arrival_date, "%Y-%m-%d") if inputs.arrival_date else now
    except ValueError:
        raise HTTPException(status_code=422, detail="arrival_date must be YYYY-MM-DD")
    hour = inputs.arrival_hour if inputs.arrival_hour is not None else now.hour
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)


def _lane_list(forecasts: dict[int, float]) -> list[LaneCongestion]:
    return [
        LaneCongestion(
            lane=lane,
            predicted_queue_length=queue,
            predicted_avg_wait_minutes=ml_models.estimate_wait_minutes(queue),
        )
        for lane, queue in sorted(forecasts.items())
    ]


def _clearance(inputs: ModelInputs, arrival: datetime, queue: float) -> float:
    return ml_models.predict_clearance_minutes(
        day_of_week=arrival.strftime("%A"),
        container_type=inputs.container_type,
        cargo_category=inputs.cargo_category,
        carrier_company=inputs.carrier,
        arrival_hour=arrival.hour,
        queue_length_at_arrival=queue,
        customs_risk_flag=inputs.customs_risk_flag,
        carrier_past_reliability_score=inputs.carrier_reliability,
        missing_documents_count=inputs.missing_documents,
    )


@router.post("/predict-clearance", response_model=ClearanceResponse)
def predict_clearance(request: ClearanceRequest):
    """Clearance-time model on its own, fed exactly what the user supplied."""
    arrival = _arrival_datetime(request)
    queue = request.queue_length
    if queue is None:
        forecasts = ml_models.get_all_lane_forecasts(arrival)
        queue = min(forecasts.values())
    return ClearanceResponse(
        predicted_minutes=_clearance(request, arrival, queue),
        queue_length_used=queue,
        arrival_datetime=arrival.isoformat(timespec="minutes"),
    )


@router.get("/congestion", response_model=CongestionResponse)
def get_congestion(at: str | None = None):
    """Per-lane forecast. `at` (YYYY-MM-DDTHH:MM) selects a time; omitted = rolling demo window."""
    when = None
    if at:
        try:
            when = datetime.fromisoformat(at)
        except ValueError:
            raise HTTPException(status_code=422, detail="at must be an ISO datetime")
    forecasts = ml_models.get_all_lane_forecasts(when)
    return CongestionResponse(
        lanes=_lane_list(forecasts),
        generated_at=datetime.now().isoformat(),
        forecast_for=when.isoformat(timespec="minutes") if when else None,
    )


@router.get("/congestion/profile")
def congestion_profile(date: str):
    """Forecast congestion for each hour of a day (worst-lane queue, wait, busy/congested status, bookings)."""
    return _run(service.get_service().congestion_profile, date)


@router.get("/lane-view")
def lane_view(date: str, hour: int):
    """All six lanes at one hour: forecast queue, wait, status and the real appointments assigned to each lane."""
    return _run(service.get_service().lane_view, date, hour)


@router.post("/assign-appointment", response_model=AppointmentResponse)
def assign_appointment(request: AppointmentRequest):
    """Joint (lane, time-slot) assignment: congestion model forecasts every lane
    for the requested arrival hour, the lowest-queue lane is picked, then the
    clearance model predicts duration for this truck using that lane's queue."""
    arrival = _arrival_datetime(request)
    forecasts = ml_models.get_all_lane_forecasts(arrival)
    best_lane = min(forecasts, key=forecasts.get)
    lane_queue = forecasts[best_lane]

    predicted_minutes = _clearance(request, arrival, lane_queue)
    wait_minutes = ml_models.estimate_wait_minutes(lane_queue)

    gate_entry = arrival + timedelta(minutes=wait_minutes)
    end_time = gate_entry + timedelta(minutes=predicted_minutes)

    fmt = "%I:%M %p"
    return AppointmentResponse(
        lane=best_lane,
        lane_queue=lane_queue,
        arrival_datetime=arrival.isoformat(timespec="minutes"),
        gate_entry_time=gate_entry.strftime(fmt),
        start_time=gate_entry.strftime(fmt),
        end_time=end_time.strftime(fmt),
        predicted_wait_minutes=wait_minutes,
        predicted_minutes=predicted_minutes,
        container_type=request.container_type,
        cargo_category=request.cargo_category,
        model_inputs={
            "day_of_week": arrival.strftime("%A"),
            "arrival_hour": arrival.hour,
            "container_type": request.container_type,
            "cargo_category": request.cargo_category,
            "carrier": request.carrier,
            "customs_risk_flag": request.customs_risk_flag,
            "carrier_reliability": request.carrier_reliability,
            "missing_documents": request.missing_documents,
            "queue_length_at_arrival": lane_queue,
        },
        lanes=_lane_list(forecasts),
    )


# ---- persisted, no-show-aware appointments ---------------------------------

def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.BookingError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/appointments")
def create_appointment(request: BookingRequest):
    """Score no-show risk, pick the slot (overbooking rule), pick the lane, predict
    clearance, and save the booking with the reasons for the decision."""
    return _run(service.get_service().create, request.model_dump())


@router.get("/appointments")
def list_appointments():
    return service.get_service().list()


@router.get("/appointments/{appointment_id}/events")
def appointment_events(appointment_id: int):
    return _run(service.get_service().events, appointment_id)


@router.post("/appointments/{appointment_id}/confirm")
def confirm_appointment(appointment_id: int):
    return _run(service.get_service().confirm, appointment_id).to_dict()


@router.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int):
    return _run(service.get_service().cancel, appointment_id).to_dict()


@router.post("/reoptimize")
def reoptimize(request: DisruptionRequest):
    """Reshuffle UNCONFIRMED bookings after a vessel delay / queue spike; confirmed stay fixed."""
    return _run(service.get_service().reoptimize, **request.model_dump())


@router.delete("/disruption")
def clear_disruption():
    service.get_service().clear_disruption()
    return {"status": "cleared"}


@router.get("/slots")
def slot_board(date: str):
    """Hourly slot load (bookings, expected arrivals, capacity, forecast wait) for one date."""
    return _run(service.get_service().slot_board, date)


REPORTS_DIR = Path(__file__).resolve().parents[2] / "ml-models" / "gate" / "reports"


@router.get("/model-metrics")
def model_metrics():
    """Evaluation results produced by the training / evaluation scripts."""
    out = {}
    for key, name in {
        "clearance_time": "clearance_time_metrics.json",
        "congestion_forecast": "congestion_forecast_metrics.json",
        "no_show": "noshow_model_metrics.json",
        "shap_importance": "noshow_shap_importance.json",
        "framework_evaluation": "framework_evaluation.json",
    }.items():
        path = REPORTS_DIR / name
        if path.exists():
            out[key] = json.loads(path.read_text())
    return out


# ---- OCR document checking -----------------------------------------------------------------

@router.post("/documents/check")
def check_document(
    file: UploadFile = File(...),
    doc_key: str = Form(...),
    appointment_id: int | None = Form(None),
    expected_container_id: str | None = Form(None),
    expected_truck_id: str | None = Form(None),
    expected_date: str | None = Form(None),
    container_type: str | None = Form(None),
):
    """OCR one uploaded document (image or PDF), classify it, extract its fields and validate
    it against the booking. With `appointment_id` the booking supplies the expected values and
    the verdict is remembered for the appointment's document submission."""
    data = file.file.read(documents.MAX_BYTES + 1)
    ctx = {
        "expected_container_id": expected_container_id,
        "expected_truck_id": expected_truck_id,
        "expected_date": expected_date,
        "container_type": container_type,
    }
    try:
        return service.get_service().check_document(data, file.filename or "", doc_key, appointment_id, ctx)
    except documents.DocumentError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except service.BookingError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError:
        raise HTTPException(status_code=503, detail="OCR engine is not installed (pip install rapidocr_onnxruntime).")


@router.get("/appointments/{appointment_id}/documents")
def appointment_documents(appointment_id: int):
    """OCR verdicts recorded so far for this appointment."""
    return _run(service.get_service().document_results, appointment_id)


@router.post("/appointments/{appointment_id}/documents/submit")
def submit_documents(appointment_id: int):
    """Submit the checked documents: counts missing/flagged ones and re-scores no-show risk and
    clearance time for the appointment."""
    return _run(service.get_service().submit_documents, appointment_id)


@router.get("/documents/templates")
def document_templates(container_type: str = "standard"):
    """What each document must contain: the required and optional details, with hints. `needed` marks the
    documents this container type must submit."""
    needed = set(documents.required_documents(container_type))
    return [{**t, "needed": t["doc_key"] in needed} for t in templates.describe_templates(container_type)]


@router.get("/documents/required")
def required_documents(container_type: str = "standard"):
    return [
        {"doc_key": k, "label": documents.DOCUMENT_LABELS[k]} for k in documents.required_documents(container_type)
    ]


# ---- conditions that are derived automatically ------------------------------------------------

@router.get("/weather")
def weather_forecast(date: str):
    """Weather severity (0 clear .. 3 storm) for a day, from the Open-Meteo forecast for the port.
    `severity` is null when the forecast is unavailable or out of range."""
    return weather.get_weather(date)


@router.get("/carriers")
def carriers():
    """Carrier profiles from the model's history: reliability and past no-show rate."""
    return noshow.carrier_profiles()


@router.get("/vessel-delay")
def vessel_delay(vessel: str, date: str):
    """Delay of a vessel on a day, from the vessel schedule (simulated until Component 1 is connected)."""
    return vessels.get_vessel_delay(vessel, date)
