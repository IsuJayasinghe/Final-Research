from typing import Literal

from pydantic import BaseModel, Field

ContainerType = Literal["standard", "reefer", "hazardous", "oversized"]
CargoCategory = Literal["export", "import"]
CustomsRisk = Literal["low", "medium", "high"]


class ModelInputs(BaseModel):
    """Every feature the trained clearance-time model consumes, as supplied by the user."""

    carrier: str
    cargo_category: CargoCategory
    container_type: ContainerType
    customs_risk_flag: CustomsRisk = "low"
    carrier_reliability: float = Field(0.75, ge=0, le=1)
    missing_documents: int = Field(0, ge=0, le=5)
    # Planned arrival at the gate, ISO date (YYYY-MM-DD) and hour of day (0-23).
    arrival_date: str | None = None
    arrival_hour: int | None = Field(None, ge=0, le=23)


class ClearanceRequest(ModelInputs):
    # Optional manual override of the queue length the model sees; when omitted
    # the forecasted queue for the chosen lane/hour is used instead.
    queue_length: float | None = Field(None, ge=0)


class ClearanceResponse(BaseModel):
    predicted_minutes: float
    queue_length_used: float
    arrival_datetime: str


class AppointmentRequest(ModelInputs):
    truck_id: str
    container_id: str


class LaneCongestion(BaseModel):
    lane: int
    predicted_queue_length: float
    predicted_avg_wait_minutes: float


class AppointmentResponse(BaseModel):
    lane: int
    lane_queue: float
    arrival_datetime: str
    gate_entry_time: str
    start_time: str
    end_time: str
    predicted_wait_minutes: float
    predicted_minutes: float
    container_type: str
    cargo_category: str
    # Echo of what was fed to the models + the forecast for every lane at that
    # hour, so the UI can show how the models reacted to the input.
    model_inputs: dict
    lanes: list[LaneCongestion]


class CongestionResponse(BaseModel):
    lanes: list[LaneCongestion]
    generated_at: str
    forecast_for: str | None = None
