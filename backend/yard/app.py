"""Smart Container Yard Allocation API (Component 3)."""
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

import yard_service
from db import get_db_connection
from predictors import (arima_forecast, forecast_occupancy, model_metrics, predict_container_dwell,
                        prophet_forecast, projected_arrivals)
from yard_service import YardError

app = Flask(__name__)
CORS(app)


@app.errorhandler(YardError)
def handle_yard_error(e):
    return jsonify({'status': 'error', 'message': str(e)}), e.status


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    code = getattr(e, 'code', 500)
    return jsonify({'status': 'error', 'message': str(e)}), code if isinstance(code, int) else 500


def ok(**payload):
    return jsonify({'status': 'success', **payload})


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise YardError('Request body must be a JSON object')
    return data


# CONTAINER ARRIVAL: predict dwell -> zone -> slot (FR01-FR06)

@app.route('/api/containers/arrival', methods=['POST'])
def container_arrival():
    """Per-container dwell prediction (XGBoost, Cell 7B), unless dwell_days is given."""
    data = body()
    arrival_time = datetime.fromisoformat(data['arrival_time']) if data.get('arrival_time') else datetime.now()
    if data.get('dwell_days') is not None:
        dwell_days, model_used = float(data['dwell_days']), 'Provided dwell time'
    else:
        dwell_days, model_used = predict_container_dwell(data, arrival_time), 'XGBoost per-container'
    return ok(**yard_service.allocate(data, dwell_days, model_used))


@app.route('/api/recommend-zone', methods=['POST'])
def recommend_zone_api():
    """Kept for earlier clients - same as /api/containers/arrival."""
    return container_arrival()


# YARD MANAGER DECISION (FR07)

@app.route('/api/allocations/<int:allocation_id>/accept', methods=['POST'])
def accept_allocation(allocation_id):
    return ok(**yard_service.accept(allocation_id))


@app.route('/api/allocations/<int:allocation_id>/override', methods=['POST'])
def override_allocation(allocation_id):
    data = body()
    return ok(**yard_service.override(allocation_id, data.get('block') or data.get('zone'), data.get('reason')))


# CONTAINER DEPARTURE

@app.route('/api/containers/<container_id>/depart', methods=['POST'])
def depart_container(container_id):
    return ok(**yard_service.depart(container_id))


# SEARCH AND TRACKING (FR09)

@app.route('/api/containers', methods=['GET'])
def list_containers():
    args = request.args
    return ok(**yard_service.search_containers(
        search=args.get('search'), container_type=args.get('type'), zone=args.get('zone'),
        status=args.get('status'), page=max(1, args.get('page', 1, type=int)),
        limit=min(100, max(1, args.get('limit', 20, type=int)))))


@app.route('/api/containers/<container_id>', methods=['GET'])
def container_details(container_id):
    """Also used by the drayage component (Component 2) to find a container's slot."""
    return ok(container=yard_service.get_container(container_id))


# YARD MAP AND DASHBOARD

@app.route('/api/yard/zones', methods=['GET'])
def yard_zones():
    return ok(**yard_service.yard_zones())


@app.route('/api/dashboard/summary', methods=['GET'])
def dashboard_summary():
    return ok(**yard_service.dashboard_summary())


# DWELL TIME FORECAST (Prophet primary, ARIMA baseline)

@app.route('/api/predict-dwell', methods=['GET'])
def predict_dwell():
    days = min(30, max(1, request.args.get('days', 7, type=int)))
    prophet_results, arima_results = prophet_forecast(days), arima_forecast(days)
    save_dwell_forecasts(prophet_results, 'Prophet')
    save_dwell_forecasts(arima_results, 'ARIMA')
    dwell_metrics = model_metrics['dwell_time']
    best = dwell_metrics['best_model']
    return ok(prophet_predictions=prophet_results, arima_predictions=arima_results,
              model_comparison={
                  'recommended': best,
                  'reason': f"Lower rolling 7-day forecast MAE ({dwell_metrics[best.lower()]['rolling_7d']['mae']:.3f} days)",
                  'prophet': dwell_metrics['prophet'], 'arima': dwell_metrics['arima']},
              note='Dates continue from the end of the training data (2021-09-20); day_ahead = days from today')


def save_dwell_forecasts(predictions, model_name):
    """Keep the latest forecast per date and model in yard.dwell_predictions."""
    conn = get_db_connection()
    if conn is None:
        return
    try:
        with conn, conn.cursor() as cur:
            dates = [p['date'] for p in predictions]
            cur.execute("""DELETE FROM yard.dwell_predictions
                           WHERE container_id IS NULL AND model_name = %s AND prediction_date = ANY(%s::date[])""",
                        (model_name, dates))
            cur.executemany("""INSERT INTO yard.dwell_predictions (prediction_date, predicted_dwell_days, model_name)
                               VALUES (%s, %s, %s)""",
                            [(p['date'], p['predicted_dwell_days'], model_name) for p in predictions])
    except Exception as db_error:
        print(f"Could not save dwell forecast: {db_error}")
    finally:
        conn.close()


# YARD OCCUPANCY FORECAST (XGBoost) + CAPACITY ALERTS (FR03, FR08)

@app.route('/api/occupancy', methods=['GET'])
def predict_occupancy():
    days = min(30, max(1, request.args.get('days', 14, type=int)))
    capacity = request.args.get('capacity', None, type=float) or yard_service.yard_zones()['total']['capacity']
    planned = projected_arrivals(days)
    forecast = forecast_occupancy(planned)

    predictions = []
    for k, (day, value) in enumerate(forecast.items()):
        utilization = round(value / capacity * 100, 1)
        predictions.append({'date': day.strftime('%Y-%m-%d'), 'day_ahead': k + 1,
                            'predicted_containers': int(round(value)), 'planned_arrivals': int(round(planned[day])),
                            'utilization_pct': utilization, 'capacity_alert': utilization >= yard_service.ZONE_ALERT_PCT})
    save_occupancy_forecasts(predictions)

    occ_metrics = model_metrics['occupancy']
    return ok(model=occ_metrics['model'], capacity=capacity, metrics=occ_metrics['next_day'],
              horizon_mape=occ_metrics['horizon_mape'], features_used=occ_metrics['features'],
              predictions=predictions, alerts=forecast_alerts(predictions))


def forecast_alerts(predictions):
    return [{'type': 'forecast_capacity', 'date': p['date'], 'day_ahead': p['day_ahead'],
             'utilization_pct': p['utilization_pct'],
             'message': f"Yard predicted to reach {p['utilization_pct']}% capacity in {p['day_ahead']} day(s)"}
            for p in predictions if p['capacity_alert']]


def save_occupancy_forecasts(predictions):
    """Keep the latest forecast per date in yard.occupancy_forecasts."""
    conn = get_db_connection()
    if conn is None:
        return
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM yard.occupancy_forecasts WHERE forecast_date = ANY(%s::date[])",
                        ([p['date'] for p in predictions],))
            cur.executemany("""INSERT INTO yard.occupancy_forecasts
                                   (forecast_date, predicted_containers, planned_arrivals, utilization_percentage, capacity_alert)
                               VALUES (%s, %s, %s, %s, %s)""",
                            [(p['date'], p['predicted_containers'], p['planned_arrivals'], p['utilization_pct'],
                              p['capacity_alert']) for p in predictions])
    except Exception as db_error:
        print(f"Could not save occupancy forecast: {db_error}")
    finally:
        conn.close()


@app.route('/api/alerts', methods=['GET'])
def alerts():
    """FR08: zones that are 85%+ full now, and days the yard is forecast to pass 85%."""
    capacity = yard_service.yard_zones()['total']['capacity']
    planned = projected_arrivals(14)
    forecast = forecast_occupancy(planned)
    predictions = [{'date': d.strftime('%Y-%m-%d'), 'day_ahead': k + 1,
                    'utilization_pct': round(v / capacity * 100, 1),
                    'capacity_alert': v / capacity * 100 >= yard_service.ZONE_ALERT_PCT}
                   for k, (d, v) in enumerate(forecast.items())]
    return ok(threshold_pct=yard_service.ZONE_ALERT_PCT,
              alerts=yard_service.zone_alerts() + forecast_alerts(predictions))


# EVALUATION RESULTS (Reports screen)

@app.route('/api/reshuffling-stats', methods=['GET'])
def reshuffling_stats():
    sim = model_metrics['reshuffling_simulation']
    return ok(simulation_results={
                  'containers_simulated': sim['containers_simulated'], 'runs': sim['runs'],
                  'reshuffles_random': sim['reshuffles_random'], 'reshuffles_ai': sim['reshuffles_ai'],
                  'reshuffles_saved': round(sim['reshuffles_random'] - sim['reshuffles_ai']),
                  'reshuffle_reduction_pct': sim['reshuffle_reduction_pct'],
                  'perfect_knowledge_reduction_pct': sim['perfect_knowledge_reduction_pct'],
                  'retrievals_without_reshuffle_pct': sim['retrievals_without_reshuffle_pct'],
                  'type_violations': sim['type_violations']},
              method='Stack simulation on real Kaggle arrivals/departures; container types follow the Colombo mix',
              conclusion=f"AI-driven placement reduces reshuffles by {sim['reshuffle_reduction_pct']:.1f}% "
                         f"and removes yard-type violations")


@app.route('/api/models/metrics', methods=['GET'])
def models_metrics():
    return ok(metrics={k: v for k, v in model_metrics.items() if k != 'reshuffling_simulation'})


# HEALTH CHECK

ENDPOINTS = [
    'POST /api/containers/arrival',
    'POST /api/allocations/<id>/accept',
    'POST /api/allocations/<id>/override',
    'POST /api/containers/<id>/depart',
    'GET  /api/containers?search=&type=&zone=&status=&page=&limit=',
    'GET  /api/containers/<id>',
    'GET  /api/yard/zones',
    'GET  /api/dashboard/summary',
    'GET  /api/predict-dwell?days=',
    'GET  /api/occupancy?days=&capacity=',
    'GET  /api/alerts',
    'GET  /api/reshuffling-stats',
    'GET  /api/models/metrics',
]


@app.route('/api/health', methods=['GET'])
def health_check():
    conn = get_db_connection()
    database = 'connected' if conn else 'unavailable'
    if conn:
        conn.close()
    return jsonify({'status': 'healthy', 'component': 'C3 - Smart Container Yard Allocation',
                    'database': database, 'containers_in_yard': len(yard_service.yard.location),
                    'models_loaded': ['Prophet', 'ARIMA', 'XGBoost occupancy', 'XGBoost per-container dwell'],
                    'endpoints': ENDPOINTS})


if __name__ == '__main__':
    print("=" * 60)
    print(" Smart Container Yard Allocation API")
    print("=" * 60)
    print(" Running on http://localhost:5001")
    for endpoint in ENDPOINTS + ['GET  /api/health']:
        print(f"   {endpoint}")
    print("=" * 60)
    app.run(debug=True, port=5001)
