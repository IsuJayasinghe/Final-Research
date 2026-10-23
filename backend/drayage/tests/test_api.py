"""
End-to-End API integration tests using FastAPI TestClient.
Covers all REST endpoints, authentication, driver data isolation, status updates, and GPS telemetry.
"""
import pytest
from fastapi.testclient import TestClient
from backend.drayage.main import app

client = TestClient(app)


def get_authenticated_headers(driver_id: str = "DRV-102", password: str = "drayage2026") -> dict:
    """Helper to obtain a valid JWT Bearer header."""
    res = client.post("/api/v1/auth/login", json={"driver_id": driver_id, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_root_endpoint():
    """Verify root API discovery endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "online"


def test_health_check_endpoint():
    """Verify health endpoint reports service and DB status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database_connected" in data


def test_login_success_and_failure():
    """Verify driver login issues JWT and rejects bad credentials."""
    # Valid login
    res_ok = client.post("/api/v1/auth/login", json={"driver_id": "DRV-102", "password": "drayage2026"})
    assert res_ok.status_code == 200
    token_data = res_ok.json()
    assert "access_token" in token_data
    assert token_data["driver"]["id"] == "DRV-102"
    assert token_data["driver"]["assigned_truck_id"] == "TRK-025"

    # Invalid login
    res_bad = client.post("/api/v1/auth/login", json={"driver_id": "DRV-102", "password": "wrong_password"})
    assert res_bad.status_code == 401


def test_driver_profile_endpoint():
    """Verify authenticated profile retrieval and unauthenticated rejection."""
    # Without token
    res_unauth = client.get("/api/v1/drivers/me")
    assert res_unauth.status_code == 401

    # With valid token
    headers = get_authenticated_headers("DRV-102")
    res_auth = client.get("/api/v1/drivers/me", headers=headers)
    assert res_auth.status_code == 200
    assert res_auth.json()["id"] == "DRV-102"


def test_update_driver_duty_status():
    """Verify duty status update (onDuty -> onBreak)."""
    headers = get_authenticated_headers("DRV-102")
    res = client.patch(
        "/api/v1/drivers/me/duty-status",
        json={"duty_status": "onBreak"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["duty_status"] == "onBreak"


def test_assigned_tasks_endpoint_and_isolation():
    """
    CRITICAL: Verify assigned tasks are returned for authenticated driver,
    and tasks assigned to another driver are NOT exposed.
    """
    headers_102 = get_authenticated_headers("DRV-102")
    res_102 = client.get("/api/v1/tasks/assigned", headers=headers_102)
    assert res_102.status_code == 200
    tasks_102 = res_102.json()
    assert len(tasks_102) > 0
    # Every task must be assigned to DRV-102
    assert all(t["assigned_driver_id"] == "DRV-102" for t in tasks_102)
    # TASK-601 belongs to DRV-105, must NOT appear in DRV-102's list
    assert not any(t["id"] == "TASK-601" for t in tasks_102)


def test_task_detail_and_forbidden_access():
    """Verify 403 Forbidden when driver attempts to view another driver's task."""
    headers_102 = get_authenticated_headers("DRV-102")

    # Own task -> HTTP 200
    res_own = client.get("/api/v1/tasks/TASK-501", headers=headers_102)
    assert res_own.status_code == 200
    assert res_own.json()["id"] == "TASK-501"

    # Other driver's task -> HTTP 403 Forbidden
    res_forbidden = client.get("/api/v1/tasks/TASK-601", headers=headers_102)
    assert res_forbidden.status_code == 403


def test_task_status_lifecycle_via_api():
    """Verify task status update API validates lifecycle transitions."""
    headers = get_authenticated_headers("DRV-102")

    # Valid transition on TASK-502: assigned -> accepted
    res_step1 = client.patch(
        "/api/v1/tasks/TASK-502/status",
        json={"status": "accepted", "notes": "Driver accepted dispatch mission."},
        headers=headers,
    )
    assert res_step1.status_code == 200
    assert res_step1.json()["status"] == "accepted"

    # Invalid jump: accepted -> completed (Must be rejected with HTTP 400)
    res_invalid = client.patch(
        "/api/v1/tasks/TASK-502/status",
        json={"status": "completed"},
        headers=headers,
    )
    assert res_invalid.status_code == 400


def test_truck_location_ingestion_api():
    """Verify GPS telemetry ingestion and driver authorization."""
    headers = get_authenticated_headers("DRV-102")

    # Valid telemetry payload
    res_ok = client.post(
        "/api/v1/locations",
        json={
            "truck_id": "TRK-025",
            "driver_id": "DRV-102",
            "latitude": 6.9428,
            "longitude": 79.8452,
            "speed_kmh": 22.4,
            "heading_degrees": 88.0,
            "accuracy_meters": 0.4,
            "current_zone": "Berth B03",
        },
        headers=headers,
    )
    assert res_ok.status_code == 201
    assert res_ok.json()["status"] == "success"

    # Mismatched driver telemetry -> 403 Forbidden
    res_mismatch = client.post(
        "/api/v1/locations",
        json={
            "truck_id": "TRK-025",
            "driver_id": "DRV-999",
            "latitude": 6.9428,
            "longitude": 79.8452,
        },
        headers=headers,
    )
    assert res_mismatch.status_code == 403
