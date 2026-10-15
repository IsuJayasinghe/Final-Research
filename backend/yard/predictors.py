"""Trained models (saved by the notebook, Cell 12) and the predictions built on them."""
import json
import os
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')

prophet_model = joblib.load(os.path.join(MODEL_DIR, 'prophet_model.pkl'))
prophet_config = joblib.load(os.path.join(MODEL_DIR, 'prophet_config.pkl'))
arima_model = joblib.load(os.path.join(MODEL_DIR, 'arima_model.pkl'))
xgb_model = joblib.load(os.path.join(MODEL_DIR, 'xgboost_model.pkl'))
dwell_bundle = joblib.load(os.path.join(MODEL_DIR, 'dwell_container_model.pkl'))
occupancy_history = pd.read_csv(os.path.join(MODEL_DIR, 'occupancy_history.csv'),
                                index_col='Date', parse_dates=True)
with open(os.path.join(MODEL_DIR, 'model_metrics.json')) as f:
    model_metrics = json.load(f)

print(" All models loaded successfully!")


# DAILY DWELL FORECASTS (Prophet primary, ARIMA baseline)
# Prophet uses daily container characteristics as regressors (notebook Cell 5). For future
# dates their values come from pre-arrival documents / vessel manifests (Component 1);
# until that integration exists, the saved average per weekday is used as projection.

def prophet_forecast(days):
    future = prophet_model.make_future_dataframe(periods=days, freq='D', include_history=False)
    projection = prophet_config['weekday_regressor_projection']
    for reg in prophet_config['regressors']:
        future[reg] = [projection[d][reg] for d in future['ds'].dt.dayofweek]
    forecast = prophet_model.predict(future)
    return [{'date': ds.strftime('%Y-%m-%d'), 'day_ahead': k + 1,
             'predicted_dwell_days': round(max(prophet_config['floor'], yhat), 2)}
            for k, (ds, yhat) in enumerate(zip(forecast['ds'], forecast['yhat']))]


def arima_forecast(days):
    values = np.asarray(arima_model.get_forecast(steps=days).predicted_mean)
    start = occupancy_history.index[-1] + timedelta(days=1)
    return [{'date': (start + timedelta(days=k)).strftime('%Y-%m-%d'), 'day_ahead': k + 1,
             'predicted_dwell_days': round(max(0, float(v)), 2)} for k, v in enumerate(values)]


# PER-CONTAINER DWELL PREDICTION (notebook Cell 7B)
# Missing optional details are passed as NaN - XGBoost handles missing values (NFR06).

def predict_container_dwell(container, arrival_time=None):
    arrival_time = arrival_time or datetime.now()
    owner = str(container.get('container_id', ''))[:4].upper()
    owners = dwell_bundle['owner_codes']

    def optional(key):
        value = container.get(key)
        return np.nan if value is None or value == '' else float(value)

    row = pd.DataFrame([{
        'Owner_Code': owner if owner in owners else 'OTHER',
        'Hour': arrival_time.hour,
        'DayOfWeek': arrival_time.weekday(),
        'Hours_Since_Baplie': optional('hours_since_baplie'),
        'Hours_Since_Berthing': optional('hours_since_berthing'),
        'Vessel_Call_Size': optional('vessel_call_size'),
        'Customs_Cleared': optional('customs_cleared'),
        'Quarantine_Flag': optional('quarantine_flag'),
        'Customs_Red_Lane': optional('customs_red_lane'),
    }])
    row['Owner_Code'] = pd.Categorical(row['Owner_Code'], categories=owners + ['OTHER'])
    prediction = float(np.expm1(dwell_bundle['model'].predict(row[dwell_bundle['features']]))[0])
    return max(0.0, prediction)


# YARD OCCUPANCY FORECAST (XGBoost, notebook Cell 7)

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


def projected_arrivals(days):
    """Incoming container projection: average arrivals per weekday from history.
    To be replaced by vessel discharge plans from Component 1 (berth / vessel ETA)."""
    recent = occupancy_history.loc[model_metrics['data']['window_start']:]
    weekday_arrivals = recent['Arrivals'].groupby(recent.index.dayofweek).mean()
    future_days = pd.date_range(occupancy_history.index[-1] + timedelta(days=1), periods=days, freq='D')
    return pd.Series(weekday_arrivals.reindex(future_days.dayofweek).values, index=future_days)


def forecast_occupancy(planned_arrivals):
    """Recursive multi-day forecast: each predicted day becomes history for the next one."""
    sim = occupancy_history[['Occupancy', 'Arrivals']].astype(float).copy()
    for day, arrivals in planned_arrivals.items():
        sim.loc[day, ['Occupancy', 'Arrivals']] = [np.nan, arrivals]
        sim.loc[day, 'Occupancy'] = xgb_model.predict(occupancy_features(sim).loc[[day]])[0]
    return sim.loc[planned_arrivals.index, 'Occupancy']
