import sys
import json
import urllib.request
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ml.prediction import load_eta_model, load_delay_model, predict_vessel_eta, assess_delay_risk

def test_all():
    print("=== STEP 1: Verifying Model Artifacts Loading ===")
    eta_artifact = load_eta_model()
    print("ETA Model loaded successfully!")
    print(f" - Model Type: {eta_artifact['metadata']['model_type']}")
    print(f" - Features: {eta_artifact['feature_columns']}")
    print(f" - MAE Metric: {eta_artifact['metrics']['mae']:.2f} hrs")

    delay_artifact = load_delay_model()
    print("\nDelay Model loaded successfully!")
    print(f" - Classifier: {type(delay_artifact['classifier']).__name__}")
    print(f" - Features: {delay_artifact['feature_columns']}")
    print(f" - ROC-AUC: {delay_artifact['metrics']['roc_auc']:.4f}")
    print(f" - F1 Score: {delay_artifact['metrics']['f1']:.4f}")

    print("\n=== STEP 2: Testing Delay & Risk Assessment Logic ===")
    # Storm scenario
    storm_telemetry = {
        "mmsi": 409321483,
        "imo_number": 9321483,
        "vessel_name": "EMMA MAERSK",
        "latitude": 6.6878,
        "longitude": 79.6253,
        "sog": 9.5,
        "cog": 195.4,
        "wind_speed_knots": 32.0,
        "wave_height_m": 3.4,
        "draft_m": 15.0,
        "distance_to_port_nmi": 55.0
    }
    storm_risk = assess_delay_risk(storm_telemetry)
    print("Storm Scenario Delay Risk:")
    print(f" - Risk Level: {storm_risk['risk_level']}")
    print(f" - Delay Probability: {storm_risk['delay_probability_percent']}%")
    print(f" - Trigger Automated Reassignment: {storm_risk['trigger_reassignment']}")
    print(f" - Triggers Detected: {storm_risk['trigger_reasons']}")
    print(f" - Action: {storm_risk['action_recommendation']}")

    # Calm scenario
    calm_telemetry = {
        "mmsi": 409321483,
        "imo_number": 9321483,
        "vessel_name": "EMMA MAERSK",
        "latitude": 6.6878,
        "longitude": 79.6253,
        "sog": 18.5,
        "cog": 195.4,
        "wind_speed_knots": 8.0,
        "wave_height_m": 0.8,
        "draft_m": 12.0,
        "distance_to_port_nmi": 55.0
    }
    calm_risk = assess_delay_risk(calm_telemetry)
    print("\nCalm Scenario Delay Risk:")
    print(f" - Risk Level: {calm_risk['risk_level']}")
    print(f" - Delay Probability: {calm_risk['delay_probability_percent']}%")
    print(f" - Trigger Automated Reassignment: {calm_risk['trigger_reassignment']}")

    print("\n=== STEP 3: Testing Integrated ETA + Delay Prediction ===")
    pred_result = predict_vessel_eta(storm_telemetry, auto_trigger_reassignment=False)
    print(f"Baseline ETA: {pred_result['eta_prediction']['baseline_eta']}")
    print(f"Dynamic ETA:  {pred_result['eta_prediction']['dynamic_eta']}")
    print(f"Weather Delay: +{pred_result['eta_prediction']['weather_delay_hours']} hrs")
    print(f"Schedule Status: {pred_result['schedule_status']}")

    print("\n=== STEP 4: FastAPI Route Handlers Verification ===")
    from app.main import (
        predict_eta,
        assess_delay_risk_endpoint,
        health_check,
        list_berths,
        get_berth_matrix,
        VesselTelemetryRequest
    )

    # 4.1 Health Check
    health = health_check()
    print("GET /api/health -> Status:", health["status"], "| DB connected:", health["database_connected"])

    # 4.2 Telemetry Request Schema validation
    telemetry_req = VesselTelemetryRequest(**storm_telemetry)
    print("VesselTelemetryRequest validated successfully for:", telemetry_req.vessel_name)

    # 4.3 POST /api/vessels/assess-delay-risk
    risk_endpoint_resp = assess_delay_risk_endpoint(telemetry_req)
    print("POST /api/vessels/assess-delay-risk -> Risk Level:", risk_endpoint_resp["risk_level"], "| Trigger Reassignment:", risk_endpoint_resp["trigger_reassignment"])

    # 4.4 POST /api/vessels/predict-eta
    eta_endpoint_resp = predict_eta(telemetry_req, auto_trigger_reassignment=False)
    print("POST /api/vessels/predict-eta -> Baseline ETA:", eta_endpoint_resp["eta_prediction"]["baseline_eta"])
    print("POST /api/vessels/predict-eta -> Dynamic ETA: ", eta_endpoint_resp["eta_prediction"]["dynamic_eta"])
    print("POST /api/vessels/predict-eta -> Weather Penalty:", eta_endpoint_resp["environmental_impact"]["weather_penalty_percent"], "%")

    # 4.5 Optional Live HTTP Daemon Check (if server running on localhost:8000)
    print("\n=== STEP 5: Live HTTP Network Check (Optional) ===")
    try:
        req_data = json.dumps(storm_telemetry).encode('utf-8')
        req = urllib.request.Request(
            'http://localhost:8000/api/vessels/assess-delay-risk',
            data=req_data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            print("HTTP Daemon is active on localhost:8000 -> Status:", response.status)
    except Exception:
        print("Note: Live HTTP server not currently listening on port 8000 (run: uvicorn main:app --reload). Route handlers verified in-process.")

    print("\nAll integration and validation checks passed successfully!")

if __name__ == "__main__":
    test_all()

