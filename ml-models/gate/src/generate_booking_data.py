"""
Synthetic truck-appointment booking dataset for the no-show / late-arrival model
(Model 2 of the Component 4 technical plan).

No real SLPA booking history is available, so - as the plan allows - bookings are
simulated under explicit, documented assumptions. Each booking gets a latent
no-show and lateness probability driven by the features the plan names as
predictors (carrier history, booking lead time, time of day, weather, traffic,
linked vessel delay) plus document/customs issues. The outcome is then sampled:

    on_time | late | no_show      (target ~ 8% no-show, ~22% late)

Carrier reliability reuses the per-carrier averages from the clearance dataset so
both models describe the same carriers. Carrier history features are computed
from PRIOR bookings only (expanding, shifted by one) so there is no label leakage.

Usage: python src/generate_booking_data.py
Writes data/raw/gate_booking_noshow_dataset_2024_2025.csv (git-ignored).
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CLEARANCE_PATH = RAW_DIR / "gate_document_clearance_dataset_2024_2025.csv"
OUT_PATH = RAW_DIR / "gate_booking_noshow_dataset_2024_2025.csv"

N_BOOKINGS = 14000
SEED = 42
TARGET_NO_SHOW = 0.08
TARGET_LATE = 0.22

# Hourly demand profile taken from the congestion dataset (mean trucks arriving).
HOURLY_DEMAND = np.array(
    [3.9, 3.9, 3.9, 3.8, 3.9, 4.8, 6.5, 8.3, 10.1, 10.8, 11.0, 10.1,
     9.2, 10.0, 11.0, 10.9, 10.1, 9.2, 7.5, 6.5, 5.7, 4.8, 4.8, 3.9]
)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def calibrate_intercept(z_without_intercept, target_rate):
    """Shift the logit so the mean probability hits the requested base rate."""
    lo, hi = -15.0, 15.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if sigmoid(z_without_intercept + mid).mean() > target_rate:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def carrier_reliability() -> dict:
    df = pd.read_csv(CLEARANCE_PATH, usecols=["carrier_company", "carrier_past_reliability_score"])
    return df.groupby("carrier_company")["carrier_past_reliability_score"].mean().to_dict()


def main():
    rng = np.random.default_rng(SEED)
    reliability = carrier_reliability()
    carriers = sorted(reliability)

    # --- booked slot: date + hour following the real hourly demand profile
    dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    day_weight = np.where(dates.dayofweek >= 5, 0.55, 1.0)
    date_idx = rng.choice(len(dates), size=N_BOOKINGS, p=day_weight / day_weight.sum())
    hours = rng.choice(24, size=N_BOOKINGS, p=HOURLY_DEMAND / HOURLY_DEMAND.sum())
    booked_slot = pd.to_datetime(dates[date_idx]) + pd.to_timedelta(hours, unit="h")

    df = pd.DataFrame({"booked_slot": booked_slot})
    df = df.sort_values("booked_slot").reset_index(drop=True)
    n = len(df)
    df["booking_id"] = np.arange(1, n + 1)
    df["date"] = df["booked_slot"].dt.normalize()
    df["booked_hour"] = df["booked_slot"].dt.hour
    df["day_of_week"] = df["booked_slot"].dt.day_name()
    df["is_weekend"] = df["booked_slot"].dt.dayofweek >= 5

    # --- booking attributes
    df["carrier_company"] = rng.choice(carriers, size=n)
    base_rel = df["carrier_company"].map(reliability).to_numpy()
    df["carrier_past_reliability_score"] = np.clip(base_rel + rng.normal(0, 0.04, n), 0.4, 0.99).round(2)
    df["container_type"] = rng.choice(
        ["standard", "reefer", "hazardous", "oversized"], size=n, p=[0.55, 0.2, 0.1, 0.15]
    )
    df["cargo_category"] = rng.choice(["export", "import"], size=n, p=[0.45, 0.55])
    df["customs_risk_flag"] = rng.choice(["low", "medium", "high"], size=n, p=[0.72, 0.2, 0.08])
    df["missing_documents_count"] = rng.choice([0, 1, 2, 3], size=n, p=[0.75, 0.15, 0.07, 0.03])
    df["booking_lead_time_hours"] = np.clip(rng.gamma(2.0, 14.0, n), 1, 120).round(1)

    month = df["booked_slot"].dt.month.to_numpy()
    monsoon = np.isin(month, [5, 6, 10, 11, 12])
    sev_p = np.where(monsoon[:, None], [[0.40, 0.30, 0.20, 0.10]], [[0.70, 0.20, 0.07, 0.03]])
    df["weather_severity"] = [rng.choice(4, p=p) for p in sev_p]
    hour = df["booked_hour"].to_numpy()
    peak = np.exp(-((hour - 9) ** 2) / 18) + np.exp(-((hour - 15) ** 2) / 18)
    df["traffic_index"] = np.clip(0.25 + 0.5 * peak + rng.normal(0, 0.08, n), 0, 1).round(2)
    df["vessel_delay_flag"] = (rng.random(n) < 0.12).astype(int)

    # --- latent outcome probabilities
    s = 1 - df["carrier_past_reliability_score"].to_numpy()
    z_ns = (
        6.0 * s
        + 0.9 * (df["missing_documents_count"].to_numpy() > 0)
        + 0.012 * df["booking_lead_time_hours"].to_numpy()
        + 0.5 * (df["customs_risk_flag"] == "high").to_numpy()
        + 0.25 * df["weather_severity"].to_numpy()
        + 0.45 * df["vessel_delay_flag"].to_numpy()
        + 0.35 * (hour < 6)
        + rng.normal(0, 0.5, n)
    )
    z_late = (
        3.0 * s
        + 1.1 * df["traffic_index"].to_numpy()
        + 0.35 * df["weather_severity"].to_numpy()
        + 0.6 * df["vessel_delay_flag"].to_numpy()
        + 0.3 * (df["missing_documents_count"].to_numpy() > 0)
        + 0.004 * df["booking_lead_time_hours"].to_numpy()
        + rng.normal(0, 0.5, n)
    )
    p_ns = sigmoid(z_ns + calibrate_intercept(z_ns, TARGET_NO_SHOW))
    p_late = sigmoid(z_late + calibrate_intercept(z_late, TARGET_LATE / (1 - TARGET_NO_SHOW)))

    no_show = rng.random(n) < p_ns
    late = (~no_show) & (rng.random(n) < p_late)
    df["status"] = np.where(no_show, "no_show", np.where(late, "late", "on_time"))

    lateness = np.where(
        late, np.clip(rng.lognormal(3.2, 0.6, n), 8, 180), np.where(no_show, np.nan, rng.normal(0, 4, n))
    )
    df["actual_lateness_minutes"] = np.round(lateness, 1)

    # --- carrier history from PRIOR bookings only (expanding mean, shifted by one)
    prior_rate, prior_weight = TARGET_NO_SHOW, 15
    ns_flag = (df["status"] == "no_show").astype(float)
    late_min = df["actual_lateness_minutes"].fillna(0).clip(lower=0)
    cum_n = df.groupby("carrier_company").cumcount()
    cum_ns = ns_flag.groupby(df["carrier_company"]).cumsum() - ns_flag
    cum_late = late_min.groupby(df["carrier_company"]).cumsum() - late_min
    df["carrier_hist_no_show_rate"] = ((cum_ns + prior_rate * prior_weight) / (cum_n + prior_weight)).round(4)
    df["carrier_hist_avg_lateness_min"] = ((cum_late + 5.0 * prior_weight) / (cum_n + prior_weight)).round(2)

    df["truck_id"] = ["TRK-" + str(x) for x in rng.integers(10000, 99999, n)]
    out = df[
        [
            "booking_id", "truck_id", "booked_slot", "date", "booked_hour", "day_of_week", "is_weekend",
            "carrier_company", "carrier_past_reliability_score", "container_type", "cargo_category",
            "customs_risk_flag", "missing_documents_count", "booking_lead_time_hours",
            "weather_severity", "traffic_index", "vessel_delay_flag",
            "carrier_hist_no_show_rate", "carrier_hist_avg_lateness_min",
            "status", "actual_lateness_minutes",
        ]
    ]
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} bookings to {OUT_PATH}")
    print(out["status"].value_counts(normalize=True).round(3).to_string())


if __name__ == "__main__":
    main()
