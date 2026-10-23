"""
Unit tests for DrayageService business logic, data isolation, and lifecycle validation.
"""
import pytest
from fastapi import HTTPException
from backend.drayage.schemas import LocationUpdatePayload, TaskStatusEnum
from backend.drayage.service import DrayageService


def test_authenticate_driver_success():
    """Verify driver can authenticate with valid credentials."""
    service = DrayageService()
    driver = service.authenticate_driver("DRV-102", "drayage2026")
    assert driver.id == "DRV-102"
    assert driver.assigned_truck_id == "TRK-025"


def test_authenticate_driver_invalid_password():
    """Verify invalid password raises HTTP 401."""
    service = DrayageService()
    with pytest.raises(HTTPException) as exc_info:
        service.authenticate_driver("DRV-102", "invalid_password")
    assert exc_info.value.status_code == 401


def test_driver_data_isolation():
    """
    CRITICAL: Verify driver DRV-102 cannot access tasks assigned to driver DRV-105.
    Must raise HTTP 403 Forbidden.
    """
    service = DrayageService()
    # DRV-102 retrieves own task -> OK
    task = service.get_task_by_id("TASK-501", driver_id="DRV-102")
    assert task.id == "TASK-501"

    # DRV-102 attempts to retrieve TASK-601 (assigned to DRV-105) -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        service.get_task_by_id("TASK-601", driver_id="DRV-102")
    assert exc_info.value.status_code == 403


def test_task_status_lifecycle_progression():
    """Verify task status progresses through canonical port lifecycle."""
    service = DrayageService()
    task_id = "TASK-502"

    # ASSIGNED -> ACCEPTED
    updated1 = service.update_task_status(task_id, "DRV-102", TaskStatusEnum.ACCEPTED.value)
    assert updated1.status == TaskStatusEnum.ACCEPTED.value

    # ACCEPTED -> TRAVELLING_TO_PICKUP
    updated2 = service.update_task_status(task_id, "DRV-102", TaskStatusEnum.TRAVELLING_TO_PICKUP.value)
    assert updated2.status == TaskStatusEnum.TRAVELLING_TO_PICKUP.value

    # ATTEMPT INVALID TRANSITION: TRAVELLING_TO_PICKUP -> COMPLETED (Must fail with 400)
    with pytest.raises(HTTPException) as exc_info:
        service.update_task_status(task_id, "DRV-102", TaskStatusEnum.COMPLETED.value)
    assert exc_info.value.status_code == 400


def test_location_ingestion_driver_mismatch_rejected():
    """Verify location update is rejected if authenticated driver does not match payload."""
    service = DrayageService()
    payload = LocationUpdatePayload(
        truck_id="TRK-025",
        driver_id="DRV-999",  # Mismatch with authenticated driver DRV-102
        latitude=6.9428,
        longitude=79.8452,
    )
    with pytest.raises(HTTPException) as exc_info:
        service.ingest_location(driver_id="DRV-102", payload=payload)
    assert exc_info.value.status_code == 403
