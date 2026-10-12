"""Component 4 (Gate Appointment) API routes.

Kept as an APIRouter so the shared backend can mount it later with
`app.include_router(gate_router)`; main.py runs it standalone for now.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

import ml_models
from schemas import (
    AppointmentRequest,
    AppointmentResponse,
    ClearanceRequest,
    ClearanceResponse,
    CongestionResponse,
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
