"""
Automated Unit and Integration Tests for Component 2 Machine Learning and Optimization.
Tests XGBoost Travel Time Predictor, Google OR-Tools Optimizer, and REST API Endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from backend.drayage.main import app
from backend.drayage.ml.predictor import TravelTimePredictor
from backend.drayage.ml.optimizer import DrayageDispatchOptimizer

client = TestClient(app)


def test_predictor_single_trip():
    """Verify XGBoost single-trip travel time inference."""
    predictor = TravelTimePredictor.get_instance()
    res = predictor.predict_trip(
        distance_meters=1450.0,
        vehicle_type="Internal_Drayage_Truck",
        route_id="RT_ECT_MAIN",
        start_zone="CICT_Berth_01",
        destination_zone="Yard_Block_A",
        departure_hour=10,  # Peak hour
    )

    assert "predicted_travel_time_seconds" in res
    assert "predicted_travel_time_minutes" in res
    assert res["predicted_travel_time_seconds"] > 60.0
    assert 2.0 <= res["predicted_travel_time_minutes"] <= 12.0
    assert res["is_peak_hour"] is True
    assert res["is_night_shift"] is False


def test_predictor_batch():
    """Verify vectorized batch inference."""
    predictor = TravelTimePredictor.get_instance()
    trips = [
        {"distance_meters": 500.0, "vehicle_type": "AGV", "route_id": "RT_SAGT_BYPASS"},
        {"distance_meters": 2000.0, "vehicle_type": "Internal_Drayage_Truck", "route_id": "RT_ECT_MAIN"},
    ]
    results = predictor.predict_batch(trips)
    assert len(results) == 2
    # Long trip should take longer than short trip
    assert results[1]["predicted_travel_time_seconds"] > results[0]["predicted_travel_time_seconds"]


def test_or_tools_optimizer_assignment():
    """Verify OR-Tools bipartite matching between trucks and tasks."""
    optimizer = DrayageDispatchOptimizer()
    trucks = [
        {"truck_id": "TRK-01", "driver_id": "DRV-101", "vehicle_type": "Internal_Drayage_Truck", "current_zone": "Yard_Block_A"},
        {"truck_id": "TRK-02", "driver_id": "DRV-102", "vehicle_type": "Internal_Drayage_Truck", "current_zone": "CICT_Berth_01"},
    ]
    tasks = [
        {"task_id": "TASK-10", "pickup_zone": "CICT_Berth_01", "destination_zone": "Yard_Block_B", "priority": 1, "distance_meters": 1300.0},
        {"task_id": "TASK-20", "pickup_zone": "Yard_Block_A", "destination_zone": "ECT_Berth_02", "priority": 2, "distance_meters": 950.0},
    ]

    solution = optimizer.optimize_dispatch(available_trucks=trucks, pending_tasks=tasks)
    assert solution["status"] in ("OPTIMAL", "FEASIBLE")
    assert solution["assignments_count"] == 2
    assert len(solution["unassigned_trucks"]) == 0
    assert len(solution["unassigned_tasks"]) == 0

    # TRK-02 should be assigned to TASK-10 (both at CICT_Berth_01)
    trk02_assign = next(a for a in solution["assignments"] if a["truck_id"] == "TRK-02")
    assert trk02_assign["task_id"] == "TASK-10"
    assert trk02_assign["empty_distance_meters"] == 50.0


def test_api_predict_travel_time():
    """Test POST /api/v1/predict-travel-time endpoint."""
    payload = {
        "distance_meters": 1250.0,
        "vehicle_type": "Internal_Drayage_Truck",
        "route_id": "RT_JCT_YARD_01",
        "start_zone": "JCT_Berth_01",
        "destination_zone": "Yard_Block_C",
        "departure_hour": 14,
        "day_of_week": 2,
    }
    response = client.post("/api/v1/predict-travel-time", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_travel_time_seconds" in data
    assert "predicted_travel_time_minutes" in data
    assert data["predicted_travel_time_seconds"] > 60.0
    assert data["departure_hour"] == 14
    assert data["is_peak_hour"] is True


def test_api_optimize_dispatch():
    """Test POST /api/v1/optimize-dispatch endpoint."""
    payload = {
        "available_trucks": [
            {"truck_id": "TRK-100", "driver_id": "DRV-102", "vehicle_type": "Internal_Drayage_Truck", "current_zone": "Yard_Block_A"},
            {"truck_id": "TRK-200", "driver_id": "DRV-105", "vehicle_type": "AGV", "current_zone": "CICT_Berth_02"},
        ],
        "pending_tasks": [
            {"task_id": "TASK-901", "pickup_zone": "CICT_Berth_02", "destination_zone": "Yard_Block_E", "priority": 1, "distance_meters": 1100.0, "route_id": "RT_SAGT_BYPASS"},
            {"task_id": "TASK-902", "pickup_zone": "Yard_Block_A", "destination_zone": "SAGT_Berth_01", "priority": 2, "distance_meters": 1600.0, "route_id": "RT_ECT_MAIN"},
        ],
        "time_limit_ms": 3000,
    }
    response = client.post("/api/v1/optimize-dispatch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["assignments_count"] == 2
    assert len(data["assignments"]) == 2


def test_api_ml_metrics():
    """Test GET /api/v1/ml-metrics endpoint and evaluate model accuracy threshold."""
    response = client.get("/api/v1/ml-metrics")
    assert response.status_code == 200
    data = response.json()
    assert "test_metrics" in data
    assert "r2_score" in data["test_metrics"]
    assert data["test_metrics"]["r2_score"] >= 0.90, "Research threshold requires R^2 >= 0.90"
    assert data["test_metrics"]["mae_seconds"] < 30.0, "MAE must be well within operational tolerance"
