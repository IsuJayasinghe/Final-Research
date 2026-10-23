"""
Pydantic Schemas and Domain Data Contracts for Component 2 (Drayage Driver System).
Bridges Flutter mobile model conventions (camelCase) with PostgreSQL relational schemas.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TaskStatusEnum(str, Enum):
    """
    Unified operational task lifecycle states.
    Supports canonical port lifecycle strings.
    """
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    TRAVELLING_TO_PICKUP = "travellingToPickup"
    AT_PICKUP = "atPickup"
    IN_TRANSIT = "inTransit"
    AT_DESTINATION = "atDestination"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @classmethod
    def from_str(cls, value: str) -> "TaskStatusEnum":
        """
        Normalize and map incoming string from DB (e.g. 'ASSIGNED', 'IN_TRANSIT')
        or Flutter (e.g. 'inTransit', 'travellingToPickup') into TaskStatusEnum.
        """
        if not value:
            return cls.ASSIGNED
        cleaned = value.strip().replace(" ", "").replace("_", "").lower()
        mapping = {
            "pending": cls.PENDING,
            "assigned": cls.ASSIGNED,
            "accepted": cls.ACCEPTED,
            "travellingtopickup": cls.TRAVELLING_TO_PICKUP,
            "atpickup": cls.AT_PICKUP,
            "intransit": cls.IN_TRANSIT,
            "atdestination": cls.AT_DESTINATION,
            "completed": cls.COMPLETED,
            "cancelled": cls.CANCELLED,
            "canceled": cls.CANCELLED,
        }
        if cleaned in mapping:
            return mapping[cleaned]
        raise ValueError(f"Unknown task status: '{value}'")

    @property
    def display_name(self) -> str:
        names = {
            self.PENDING: "Pending",
            self.ASSIGNED: "Assigned",
            self.ACCEPTED: "Accepted",
            self.TRAVELLING_TO_PICKUP: "Travelling to Pickup",
            self.AT_PICKUP: "At Pickup",
            self.IN_TRANSIT: "In Transit",
            self.AT_DESTINATION: "At Destination",
            self.COMPLETED: "Completed",
            self.CANCELLED: "Cancelled",
        }
        return names.get(self, self.value)

    @property
    def allowed_transitions(self) -> List["TaskStatusEnum"]:
        """Strict operational state machine transition rules."""
        transitions: Dict[TaskStatusEnum, List[TaskStatusEnum]] = {
            TaskStatusEnum.PENDING: [TaskStatusEnum.ASSIGNED, TaskStatusEnum.CANCELLED],
            TaskStatusEnum.ASSIGNED: [TaskStatusEnum.ACCEPTED, TaskStatusEnum.CANCELLED],
            TaskStatusEnum.ACCEPTED: [TaskStatusEnum.TRAVELLING_TO_PICKUP, TaskStatusEnum.CANCELLED],
            TaskStatusEnum.TRAVELLING_TO_PICKUP: [TaskStatusEnum.AT_PICKUP, TaskStatusEnum.CANCELLED],
            TaskStatusEnum.AT_PICKUP: [TaskStatusEnum.IN_TRANSIT, TaskStatusEnum.CANCELLED],
            TaskStatusEnum.IN_TRANSIT: [TaskStatusEnum.AT_DESTINATION, TaskStatusEnum.CANCELLED],
            TaskStatusEnum.AT_DESTINATION: [TaskStatusEnum.COMPLETED],
            TaskStatusEnum.COMPLETED: [],
            TaskStatusEnum.CANCELLED: [],
        }
        return transitions.get(self, [])

    def can_transition_to(self, target: "TaskStatusEnum") -> bool:
        return target in self.allowed_transitions


class DriverDutyStatusEnum(str, Enum):
    ON_DUTY = "onDuty"
    ON_BREAK = "onBreak"
    OFF_DUTY = "offDuty"

    @classmethod
    def from_str(cls, value: str) -> "DriverDutyStatusEnum":
        cleaned = value.strip().replace(" ", "").replace("_", "").lower()
        if "duty" in cleaned and "off" not in cleaned:
            return cls.ON_DUTY
        if "break" in cleaned:
            return cls.ON_BREAK
        if "off" in cleaned:
            return cls.OFF_DUTY
        if "available" in cleaned:
            return cls.ON_DUTY
        return cls.ON_DUTY


class DriverLoginRequest(BaseModel):
    driver_id: str = Field(..., min_length=2, max_length=50, description="Driver ID (e.g. DRV-102)")
    password: str = Field(..., min_length=4, description="Terminal password")


class DriverResponse(BaseModel):
    id: str
    name: str
    phone: str
    duty_status: str
    assigned_truck_id: Optional[str] = None
    shift_hours_completed: float = 4.5
    shift_hours_max: float = 8.0


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    driver: DriverResponse


class TruckResponse(BaseModel):
    id: str
    license_plate: str
    vehicle_type: str
    current_status: str
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    current_zone: Optional[str] = None


class TaskResponse(BaseModel):
    """
    Unified task response matching the Flutter TransportTask domain model.
    Joins drayage.transport_tasks, drayage.truck_assignments, common.containers, common.vessels.
    """
    id: str
    vessel_id: str
    vessel_name: str
    container_id: str
    container_type: str
    container_iso: str
    container_weight_tons: float
    pickup_zone: str
    destination_zone: str
    priority: str
    status: str
    scheduled_pickup: str
    estimated_arrival: Optional[str] = None
    assigned_truck_id: str
    assigned_driver_id: str
    route_id: Optional[str] = None
    distance_meters: float = 0.0
    estimated_travel_minutes: Optional[float] = None
    special_instructions: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status name (e.g. 'accepted', 'inTransit')")
    notes: Optional[str] = Field(None, description="Optional operational notes or reason")

    @field_validator("status")
    @classmethod
    def validate_and_normalize_status(cls, v: str) -> str:
        enum_val = TaskStatusEnum.from_str(v)
        return enum_val.value


class DutyStatusUpdateRequest(BaseModel):
    duty_status: str = Field(..., description="Target duty status ('onDuty', 'onBreak', 'offDuty')")

    @field_validator("duty_status")
    @classmethod
    def validate_and_normalize_duty(cls, v: str) -> str:
        enum_val = DriverDutyStatusEnum.from_str(v)
        return enum_val.value


class LocationUpdatePayload(BaseModel):
    truck_id: str = Field(..., min_length=2, max_length=50)
    driver_id: str = Field(..., min_length=2, max_length=50)
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    speed_kmh: float = Field(0.0, ge=0.0, le=150.0, description="Vehicle speed in km/h")
    heading_degrees: float = Field(0.0, ge=0.0, le=360.0, description="Compass heading 0-360")
    accuracy_meters: float = Field(0.0, ge=0.0, description="GPS fix horizontal accuracy in meters")
    recorded_at: Optional[datetime] = None
    current_zone: Optional[str] = None

    @field_validator("recorded_at", mode="before")
    @classmethod
    def default_recorded_at(cls, v: Any) -> datetime:
        if v is None:
            return datetime.now(timezone.utc)
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v


class LocationUpdateResponse(BaseModel):
    status: str = "success"
    message: str
    location_id: Optional[int] = None
    recorded_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database_connected: bool
    timestamp: datetime


# ==============================================================================
# Component 2 Machine Learning & Optimization Schemas
# ==============================================================================

class TravelTimePredictionRequest(BaseModel):
    distance_meters: float = Field(..., ge=10.0, le=25000.0, description="Transport distance in meters")
    vehicle_type: str = Field("Internal_Drayage_Truck", description="Vehicle type (AGV or Internal_Drayage_Truck)")
    route_id: str = Field("RT_ECT_MAIN", description="Assigned terminal corridor")
    start_zone: str = Field("CICT_Berth_01", description="Origin terminal zone or berth")
    destination_zone: str = Field("Yard_Block_A", description="Destination yard block or berth")
    departure_hour: Optional[int] = Field(None, ge=0, le=23, description="Departure hour (0-23)")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Mon, 6=Sun)")


class TravelTimePredictionResponse(BaseModel):
    predicted_travel_time_seconds: float
    predicted_travel_time_minutes: float
    distance_meters: float
    vehicle_type: str
    route_id: str
    start_zone: str
    destination_zone: str
    departure_hour: int
    is_peak_hour: bool
    is_night_shift: bool


class AvailableTruckInput(BaseModel):
    truck_id: str = Field(..., min_length=2)
    driver_id: Optional[str] = None
    vehicle_type: str = "Internal_Drayage_Truck"
    current_zone: Optional[str] = "Yard_Block_A"


class PendingTaskInput(BaseModel):
    task_id: str = Field(..., min_length=2)
    pickup_zone: str
    destination_zone: str
    priority: int = Field(1, ge=1, le=5)
    distance_meters: Optional[float] = 1200.0
    route_id: Optional[str] = "RT_ECT_MAIN"


class DispatchOptimizationRequest(BaseModel):
    available_trucks: List[AvailableTruckInput] = Field(..., min_length=1)
    pending_tasks: List[PendingTaskInput] = Field(..., min_length=1)
    time_limit_ms: Optional[int] = Field(5000, ge=500, le=30000)


class OptimizedAssignment(BaseModel):
    truck_id: str
    driver_id: Optional[str] = None
    task_id: str
    pickup_zone: str
    destination_zone: str
    priority: int
    empty_distance_meters: float
    empty_travel_minutes: float
    estimated_travel_minutes: float
    total_estimated_cycle_minutes: float


class DispatchOptimizationResponse(BaseModel):
    status: str
    assignments_count: int
    assignments: List[OptimizedAssignment]
    unassigned_trucks: List[str]
    unassigned_tasks: List[str]
    solver_duration_ms: float

