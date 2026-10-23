"""
FastAPI Router for Component 2: Intelligent Drayage Truck Optimization System.
Provides RESTful endpoints for terminal truck driver workflow, task lifecycle, and telemetry.
"""
import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import check_database_connection, get_db
from .schemas import (
    DispatchOptimizationRequest,
    DispatchOptimizationResponse,
    DriverLoginRequest,
    DriverResponse,
    DutyStatusUpdateRequest,
    HealthResponse,
    LocationUpdatePayload,
    LocationUpdateResponse,
    StatusUpdateRequest,
    TaskResponse,
    TokenResponse,
    TravelTimePredictionRequest,
    TravelTimePredictionResponse,
)
from .security import create_access_token, get_current_driver_id
from .service import DrayageService
from .ml.predictor import TravelTimePredictor
from .ml.optimizer import DrayageDispatchOptimizer

router = APIRouter(tags=["Component 2: Drayage Truck Optimization"])


@router.get("/health", response_model=HealthResponse)
def get_health():
    """
    Service health check endpoint.
    Reports operational status and live PostgreSQL connectivity.
    """
    db_connected = check_database_connection()
    return HealthResponse(
        status="healthy",
        service="Component 2: Drayage Truck Optimization API",
        version="1.0.0",
        database_connected=db_connected,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(
    payload: DriverLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate driver by ID and terminal password.
    Returns a signed JWT bearer token containing the driver session.
    """
    service = DrayageService(db=db)
    driver = service.authenticate_driver(payload.driver_id, payload.password)
    
    # Generate JWT bearer token
    token = create_access_token(data={"sub": driver.id, "name": driver.name})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=720,
        driver=driver,
    )


@router.get("/drivers/me", response_model=DriverResponse)
def get_current_driver_profile(
    current_driver_id: str = Depends(get_current_driver_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve profile and assigned vehicle details for the authenticated driver.
    Identity is verified strictly from the bearer token.
    """
    service = DrayageService(db=db)
    return service.get_driver_profile(current_driver_id)


@router.patch("/drivers/me/duty-status", response_model=DriverResponse)
def update_driver_duty_status(
    payload: DutyStatusUpdateRequest,
    current_driver_id: str = Depends(get_current_driver_id),
    db: Session = Depends(get_db),
):
    """
    Update duty status (onDuty, onBreak, offDuty) for the authenticated driver.
    """
    service = DrayageService(db=db)
    return service.update_driver_duty_status(current_driver_id, payload.duty_status)


@router.get("/tasks/assigned", response_model=List[TaskResponse])
def get_assigned_tasks(
    current_driver_id: str = Depends(get_current_driver_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve active container transport tasks assigned to the authenticated driver.
    Enforces driver-level data isolation.
    """
    service = DrayageService(db=db)
    return service.get_assigned_tasks(current_driver_id)


@router.get("/tasks/history", response_model=List[TaskResponse])
def get_task_history(
    current_driver_id: str = Depends(get_current_driver_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve completed task history for the current shift.
    """
    service = DrayageService(db=db)
    return service.get_completed_tasks(current_driver_id)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_details(
    task_id: str,
    current_driver_id: str = Depends(get_current_driver_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve details for a specific task.
    Enforces driver authorization: returns 403 Forbidden if assigned to another driver.
    """
    service = DrayageService(db=db)
    return service.get_task_by_id(task_id, current_driver_id)


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
def update_task_status(
    task_id: str,
    payload: StatusUpdateRequest,
    current_driver_id: str = Depends(get_current_driver_id),
    db: Session = Depends(get_db),
):
    """
    Validate and execute an operational task status transition.
    Enforces strict port lifecycle rules (e.g. accepted -> travellingToPickup -> atPickup -> inTransit -> atDestination -> completed).
    Rejects invalid out-of-order transitions with HTTP 400.
    """
    service = DrayageService(db=db)
    return service.update_task_status(
        task_id=task_id,
        driver_id=current_driver_id,
        target_status=payload.status,
        notes=payload.notes,
    )


@router.post("/locations", response_model=LocationUpdateResponse, status_code=status.HTTP_201_CREATED)
def record_truck_location(
    payload: LocationUpdatePayload,
    current_driver_id: str = Depends(get_current_driver_id),
    db: Session = Depends(get_db),
):
    """
    Ingest periodic truck GPS telemetry.
    Validates coordinates, heading, and driver authorization before persisting.
    """
    service = DrayageService(db=db)
    return service.ingest_location(current_driver_id, payload)


# ==============================================================================
# Component 2 Machine Learning & Optimization Endpoints
# ==============================================================================

@router.post("/predict-travel-time", response_model=TravelTimePredictionResponse)
def predict_travel_time(payload: TravelTimePredictionRequest):
    """
    Predict container transport travel time using the trained XGBoost model.
    Factors in route distance, vehicle type kinematics, and corridor congestion.
    """
    try:
        predictor = TravelTimePredictor.get_instance()
        result = predictor.predict_trip(
            distance_meters=payload.distance_meters,
            vehicle_type=payload.vehicle_type,
            route_id=payload.route_id,
            start_zone=payload.start_zone,
            destination_zone=payload.destination_zone,
            departure_hour=payload.departure_hour,
            day_of_week=payload.day_of_week,
        )
        return TravelTimePredictionResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Travel time prediction failed: {str(e)}",
        )


@router.post("/optimize-dispatch", response_model=DispatchOptimizationResponse)
def optimize_truck_dispatch(payload: DispatchOptimizationRequest):
    """
    Run the Google OR-Tools optimization engine to find optimal truck-to-task assignments.
    Minimizes total operational cycle time (deadhead travel + loaded travel) and prioritizes urgent tasks.
    """
    try:
        optimizer = DrayageDispatchOptimizer()
        trucks = [t.model_dump() for t in payload.available_trucks]
        tasks = [j.model_dump() for j in payload.pending_tasks]
        solution = optimizer.optimize_dispatch(
            available_trucks=trucks,
            pending_tasks=tasks,
            time_limit_ms=payload.time_limit_ms or 5000,
        )
        return DispatchOptimizationResponse(**solution)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}",
        )


@router.get("/ml-metrics")
def get_ml_metrics():
    """
    Return training and test performance metrics (MAE, RMSE, R^2) and model metadata.
    """
    metrics_path = Path(__file__).resolve().parent / "ml" / "models" / "model_metrics.json"
    if not metrics_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ML metrics not found. Model might not be trained yet.",
        )
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)

