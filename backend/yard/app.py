from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd
from datetime import timedelta
import psycopg2
import json
import os

app = Flask(__name__)
CORS(app)


# LOAD SAVED MODELS

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')

prophet_model = joblib.load(os.path.join(MODEL_DIR, 'prophet_model.pkl'))
prophet_config = joblib.load(os.path.join(MODEL_DIR, 'prophet_config.pkl'))
arima_model = joblib.load(os.path.join(MODEL_DIR, 'arima_model.pkl'))
xgb_model = joblib.load(os.path.join(MODEL_DIR, 'xgboost_model.pkl'))
occupancy_history = pd.read_csv(os.path.join(MODEL_DIR, 'occupancy_history.csv'),
                                index_col='Date', parse_dates=True)

# Evaluation metrics written by the notebook (Cell 12)
with open(os.path.join(MODEL_DIR, 'model_metrics.json')) as f:
    model_metrics = json.load(f)

print(" All models loaded successfully!")


# PROPHET FORECAST HELPER
# Prophet uses daily container characteristics as regressors (notebook Cell 5). For future
# dates their values come from pre-arrival documents / vessel manifests (Component 1);
# until that integration exists, the saved average per weekday is used as projection.

def prophet_forecast(days):
    future = prophet_model.make_future_dataframe(periods=days, freq='D', include_history=False)
    projection = prophet_config['weekday_regressor_projection']
    for reg in prophet_config['regressors']:
        future[reg] = [projection[d][reg] for d in future['ds'].dt.dayofweek]
    return future, prophet_model.predict(future)


# OCCUPANCY FORECAST HELPERS (same features as notebook Cell 7)

OCC_FEATURES = model_metrics['occupancy']['features']

def occupancy_features(hist):
    X = pd.DataFrame(index=hist.index)
    X['Occ_Prev'] = hist['Occupancy'].shift(1)
    X['Occ_Prev2'] = hist['Occupancy'].shift(2)
    X['Occ_Prev7'] = hist['Occupancy'].shift(7)
    X['Arr_Today'] = hist['Arrivals']
    X['Arr_Prev1'] = hist['Arrivals'].shift(1)
    X['Arr_Prev2'] = hist['Arrivals'].shift(2)
    X['Arr_Prev3_7'] = hist['Arrivals'].shift(3).rolling(5).sum()
    X['DayOfWeek'] = hist.index.dayofweek
    return X[OCC_FEATURES]

def forecast_occupancy(planned_arrivals):
    """Recursive multi-day forecast: each predicted day becomes history for the next one."""
    sim = occupancy_history[['Occupancy', 'Arrivals']].astype(float).copy()
    for day, arrivals in planned_arrivals.items():
        sim.loc[day, ['Occupancy', 'Arrivals']] = [np.nan, arrivals]
        sim.loc[day, 'Occupancy'] = xgb_model.predict(occupancy_features(sim).loc[[day]])[0]
    return sim.loc[planned_arrivals.index, 'Occupancy']



# DATABASE CONNECTION

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'smart_port_db',
    'user': 'postgres',
    'password': os.environ.get('DB_PASSWORD', '')
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None



# ZONE RECOMMENDATION FUNCTION

def recommend_zone(dwell_days, container_type):
    if container_type == 'REEFER':
        return 'Reefer_Yard_01', 'Temperature controlled storage required'
    elif container_type == 'HAZMAT':
        return 'Hazardous_Yard_01', 'Safety regulations - isolated storage'
    elif container_type == 'OVERSIZED':
        if dwell_days <= 3:
            return 'Oversized_Short_Term', 'Oversized container - short stay'
        else:
            return 'Oversized_Long_Term', 'Oversized container - extended stay'

    # Standard DRY containers - based on dwell time
    if dwell_days <= 3:
        return 'Short-Term Zone', f'Short dwell time ({dwell_days:.1f} days)'
    elif dwell_days <= 7:
        return 'Medium-Term Zone', f'Medium dwell time ({dwell_days:.1f} days)'
    else:
        return 'Long-Term Zone', f'Long dwell time ({dwell_days:.1f} days)'


# ENDPOINT 1: PREDICT DWELL TIME (Prophet + ARIMA)

@app.route('/api/predict-dwell', methods=['GET'])
def predict_dwell():
    try:
        days = request.args.get('days', 7, type=int)

        # Prophet prediction
        future, forecast = prophet_forecast(days)

        prophet_results = []
        for _, row in forecast.iterrows():
            prophet_results.append({
                'date': row['ds'].strftime('%Y-%m-%d'),
                'predicted_dwell_days': round(max(prophet_config['floor'], row['yhat']), 2)
            })

        # ARIMA prediction (same future dates as Prophet)
        arima_forecast = np.asarray(arima_model.get_forecast(steps=days).predicted_mean)
        arima_results = []
        for date, val in zip(future['ds'], arima_forecast):
            arima_results.append({
                'date': date.strftime('%Y-%m-%d'),
                'predicted_dwell_days': round(max(0, float(val)), 2)
            })

        dwell_metrics = model_metrics['dwell_time']
        best = dwell_metrics['best_model']
        return jsonify({
            'status': 'success',
            'prophet_predictions': prophet_results,
            'arima_predictions': arima_results,
            'model_comparison': {
                'recommended': best,
                'reason': f"Lower rolling 7-day forecast MAE "
                          f"({dwell_metrics[best.lower()]['rolling_7d']['mae']:.3f} days)",
                'prophet': dwell_metrics['prophet']['rolling_7d'],
                'arima': dwell_metrics['arima']['rolling_7d']
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



# ENDPOINT 2: RECOMMEND ZONE

@app.route('/api/recommend-zone', methods=['POST'])
def recommend_zone_api():
    try:
        data = request.get_json()
        container_type = data.get('container_type', 'DRY')
        dwell_days = data.get('dwell_days', None)
        container_id = data.get('container_id', 'UNKNOWN')

        # If no dwell_days given, use Prophet to predict
        if dwell_days is None:
            _, forecast = prophet_forecast(1)
            dwell_days = max(prophet_config['floor'], forecast['yhat'].iloc[-1])

        zone, reason = recommend_zone(dwell_days, container_type)

        # Save to database
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO zone_allocations
                    (container_id, container_type, dwell_days, recommended_zone, reason)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (container_id, container_type, dwell_days, zone, reason)
                )
                conn.commit()
                cur.close()
                conn.close()
            except Exception as db_error:
                print(f"DB save error: {db_error}")

        return jsonify({
            'status': 'success',
            'container_id': container_id,
            'container_type': container_type,
            'predicted_dwell_days': round(dwell_days, 2),
            'recommended_zone': zone,
            'reason': reason
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ENDPOINT 3: OCCUPANCY PREDICTION - XGBoost

@app.route('/api/occupancy', methods=['GET'])
def predict_occupancy():
    try:
        days = request.args.get('days', 14, type=int)
        capacity = request.args.get('capacity', None, type=float)

        # Incoming container projection: average arrivals per weekday from history.
        # To be replaced by vessel discharge plans from Component 1 (berth / vessel ETA).
        recent = occupancy_history.loc[model_metrics['data']['window_start']:]
        weekday_arrivals = recent['Arrivals'].groupby(recent.index.dayofweek).mean()
        future_days = pd.date_range(occupancy_history.index[-1] + timedelta(days=1), periods=days, freq='D')
        planned = pd.Series(weekday_arrivals.reindex(future_days.dayofweek).values, index=future_days)
        forecast = forecast_occupancy(planned)

        predictions = []
        for day, value in forecast.items():
            entry = {'date': day.strftime('%Y-%m-%d'), 'predicted_containers': int(round(value)),
                     'planned_arrivals': int(round(planned[day]))}
            if capacity:
                entry['utilization_pct'] = round(value / capacity * 100, 1)
            predictions.append(entry)

        alerts = []
        if capacity:
            alerts = [f"Yard predicted to reach {p['utilization_pct']}% capacity on {p['date']}"
                      for p in predictions if p['utilization_pct'] >= 85]

        occ_metrics = model_metrics['occupancy']
        return jsonify({
            'status': 'success',
            'model': occ_metrics['model'],
            'metrics': occ_metrics['next_day'],
            'horizon_mape': occ_metrics['horizon_mape'],
            'features_used': occ_metrics['features'],
            'predictions': predictions,
            'alerts': alerts
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



# ENDPOINT 4: RESHUFFLING SIMULATION STATS

@app.route('/api/reshuffling-stats', methods=['GET'])
def reshuffling_stats():
    try:
        sim = model_metrics['reshuffling_simulation']
        return jsonify({
            'status': 'success',
            'simulation_results': {
                'containers_simulated': sim['containers_simulated'],
                'runs': sim['runs'],
                'reshuffles_random': sim['reshuffles_random'],
                'reshuffles_ai': sim['reshuffles_ai'],
                'reshuffles_saved': round(sim['reshuffles_random'] - sim['reshuffles_ai']),
                'reshuffle_reduction_pct': sim['reshuffle_reduction_pct'],
                'perfect_knowledge_reduction_pct': sim['perfect_knowledge_reduction_pct'],
                'retrievals_without_reshuffle_pct': sim['retrievals_without_reshuffle_pct'],
                'type_violations': sim['type_violations']
            },
            'method': 'Stack simulation on real Kaggle arrivals/departures; container types follow the Colombo mix',
            'conclusion': f"AI-driven placement reduces reshuffles by {sim['reshuffle_reduction_pct']:.1f}% "
                          f"and removes yard-type violations"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



# HEALTH CHECK

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'component': 'C3 - Smart Container Yard Allocation',
        'models_loaded': ['Prophet', 'ARIMA', 'XGBoost'],
        'endpoints': [
            'GET  /api/predict-dwell',
            'POST /api/recommend-zone',
            'GET  /api/occupancy',
            'GET  /api/reshuffling-stats'
        ]
    })



# RUN SERVER

if __name__ == '__main__':
    print("=" * 60)
    print(" Smart Container Yard Allocation API")
    print("=" * 60)
    print(" Running on http://localhost:5001")
    print(" Endpoints:")
    print("   GET  /api/predict-dwell")
    print("   POST /api/recommend-zone")
    print("   GET  /api/occupancy")
    print("   GET  /api/reshuffling-stats")
    print("   GET  /api/health")
    print("=" * 60)
    app.run(debug=True, port=5001)