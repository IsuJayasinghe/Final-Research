"""
Unit tests for Component 2 schemas, lifecycle validators, and domain contracts.
"""
import pytest
from pydantic import ValidationError
from backend.drayage.schemas import (
    DriverDutyStatusEnum,
    LocationUpdatePayload,
    StatusUpdateRequest,
    TaskStatusEnum,
)


def test_task_status_enum_normalization():
    """Verify task statuses from database and Flutter format normalize to canonical enum."""
    assert TaskStatusEnum.from_str("ASSIGNED") == TaskStatusEnum.ASSIGNED
    assert TaskStatusEnum.from_str("assigned") == TaskStatusEnum.ASSIGNED
    assert TaskStatusEnum.from_str("TRAVELLING_TO_PICKUP") == TaskStatusEnum.TRAVELLING_TO_PICKUP
    assert TaskStatusEnum.from_str("travellingToPickup") == TaskStatusEnum.TRAVELLING_TO_PICKUP
    assert TaskStatusEnum.from_str("IN_TRANSIT") == TaskStatusEnum.IN_TRANSIT
    assert TaskStatusEnum.from_str("inTransit") == TaskStatusEnum.IN_TRANSIT
    assert TaskStatusEnum.from_str("AT_DESTINATION") == TaskStatusEnum.AT_DESTINATION
    assert TaskStatusEnum.from_str("atDestination") == TaskStatusEnum.AT_DESTINATION
    assert TaskStatusEnum.from_str("COMPLETED") == TaskStatusEnum.COMPLETED
    assert TaskStatusEnum.from_str("completed") == TaskStatusEnum.COMPLETED


def test_task_status_transition_rules():
    """Verify operational lifecycle transitions follow strict terminal rules."""
    # Permitted forward transitions
    assert TaskStatusEnum.ASSIGNED.can_transition_to(TaskStatusEnum.ACCEPTED)
    assert TaskStatusEnum.ACCEPTED.can_transition_to(TaskStatusEnum.TRAVELLING_TO_PICKUP)
    assert TaskStatusEnum.TRAVELLING_TO_PICKUP.can_transition_to(TaskStatusEnum.AT_PICKUP)
    assert TaskStatusEnum.AT_PICKUP.can_transition_to(TaskStatusEnum.IN_TRANSIT)
    assert TaskStatusEnum.IN_TRANSIT.can_transition_to(TaskStatusEnum.AT_DESTINATION)
    assert TaskStatusEnum.AT_DESTINATION.can_transition_to(TaskStatusEnum.COMPLETED)

    # Prohibited transitions
    assert not TaskStatusEnum.ASSIGNED.can_transition_to(TaskStatusEnum.COMPLETED)
    assert not TaskStatusEnum.ASSIGNED.can_transition_to(TaskStatusEnum.IN_TRANSIT)
    assert not TaskStatusEnum.COMPLETED.can_transition_to(TaskStatusEnum.ACCEPTED)
    assert not TaskStatusEnum.IN_TRANSIT.can_transition_to(TaskStatusEnum.ACCEPTED)


def test_status_update_request_validator():
    """Verify StatusUpdateRequest normalizes camelCase and snake_case."""
    req1 = StatusUpdateRequest(status="inTransit")
    assert req1.status == "inTransit"

    req2 = StatusUpdateRequest(status="IN_TRANSIT")
    assert req2.status == "inTransit"

    with pytest.raises(ValueError):
        StatusUpdateRequest(status="INVALID_STATUS_XYZ")


def test_driver_duty_status_normalization():
    """Verify duty status normalization."""
    assert DriverDutyStatusEnum.from_str("onDuty") == DriverDutyStatusEnum.ON_DUTY
    assert DriverDutyStatusEnum.from_str("AVAILABLE") == DriverDutyStatusEnum.ON_DUTY
    assert DriverDutyStatusEnum.from_str("onBreak") == DriverDutyStatusEnum.ON_BREAK
    assert DriverDutyStatusEnum.from_str("offDuty") == DriverDutyStatusEnum.OFF_DUTY


def test_location_update_payload_validation():
    """Verify GPS telemetry coordinate bounds and fields."""
    valid_payload = LocationUpdatePayload(
        truck_id="TRK-025",
        driver_id="DRV-102",
        latitude=6.9428,
        longitude=79.8452,
        speed_kmh=18.5,
        heading_degrees=84.0,
        accuracy_meters=0.5,
    )
    assert valid_payload.truck_id == "TRK-025"
    assert valid_payload.latitude == 6.9428
    assert valid_payload.longitude == 79.8452

    # Reject out-of-range coordinates
    with pytest.raises(ValidationError):
        LocationUpdatePayload(
            truck_id="TRK-025",
            driver_id="DRV-102",
            latitude=120.0,  # Invalid latitude > 90
            longitude=79.8452,
        )

    with pytest.raises(ValidationError):
        LocationUpdatePayload(
            truck_id="TRK-025",
            driver_id="DRV-102",
            latitude=6.9428,
            longitude=-200.0,  # Invalid longitude < -180
        )
