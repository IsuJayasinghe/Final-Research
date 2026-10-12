"""
No-show / late-arrival risk inference with SHAP explanations (Model 2).

Loads the serving model trained by ml-models/gate/src/train_noshow_model.py and
scores a single booking: P(on_time), P(late), P(no_show). For the no_show class it
also returns the top SHAP factors as plain-language reasons, so a booking that is
overbooked, bumped or reassigned can always be explained to the driver/company.
"""

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

MODELS_DIR = Path(__file__).resolve().parent / "models"

# Fallbacks for carriers the model has never seen (training-data averages).
DEFAULT_HIST_NO_SHOW_RATE = 0.08
DEFAULT_HIST_AVG_LATENESS_MIN = 7.0

_artifact: dict | None = None
_explainer = None
_feature_names: list[str] = []


def load_model() -> None:
    global _artifact, _explainer, _feature_names
    _artifact = joblib.load(MODELS_DIR / "noshow_model.joblib")
    pipe = _artifact["pipeline"]
    pre, model = pipe.named_steps["preprocess"], pipe.named_steps["model"]
    _feature_names = [n.split("__", 1)[1] for n in pre.get_feature_names_out()]
    if _artifact["family"] == "xgboost":
        _explainer = shap.TreeExplainer(model)
    else:
        _explainer = shap.LinearExplainer(model, _artifact["background"])


def traffic_index_for_hour(hour: int) -> float:
    """Typical road-traffic level by hour (peaks 09:00 and 15:00), as in the training data."""
    peak = np.exp(-((hour - 9) ** 2) / 18) + np.exp(-((hour - 15) ** 2) / 18)
    return float(np.clip(0.25 + 0.5 * peak, 0, 1))


def _label(feature: str, row: pd.Series) -> str:
    """Human-readable phrase for one model feature given this booking's value."""
    if feature.startswith("customs_risk_flag_"):
        return f"{feature.rsplit('_', 1)[1]} customs risk"
    if feature.startswith("container_type_"):
        return f"{feature.rsplit('_', 1)[1]} container"
    if feature.startswith("cargo_category_"):
        return f"{feature.rsplit('_', 1)[1]} cargo"
    if feature.startswith("day_of_week_"):
        return f"{feature.split('_', 3)[3]} arrival"
    v = row.get(feature)
    return {
        "missing_documents_count": f"{int(v)} missing document(s)",
        "carrier_past_reliability_score": f"carrier reliability {v:.2f}",
        "booking_lead_time_hours": f"booked {v:.0f}h in advance",
        "booked_hour": f"arrival hour {int(v):02d}:00",
        "weather_severity": f"weather severity {int(v)}/3",
        "vessel_delay_flag": "linked vessel is delayed" if v else "linked vessel on time",
        "traffic_index": f"road traffic index {v:.2f}",
        "carrier_hist_no_show_rate": f"carrier's past no-show rate {v:.1%}",
        "carrier_hist_avg_lateness_min": f"carrier's average lateness {v:.0f} min",
    }.get(feature, feature.replace("_", " "))


def build_row(
    *,
    arrival: datetime,
    carrier: str,
    container_type: str,
    cargo_category: str,
    customs_risk_flag: str,
    missing_documents: int,
    carrier_reliability: float,
    lead_time_hours: float,
    weather_severity: int = 0,
    vessel_delay: bool = False,
    traffic_index: float | None = None,
) -> pd.DataFrame:
    hist = _artifact["carrier_history"].get(carrier, {})
    return pd.DataFrame(
        [
            {
                "day_of_week": arrival.strftime("%A"),
                "container_type": container_type,
                "cargo_category": cargo_category,
                "customs_risk_flag": customs_risk_flag,
                "booked_hour": arrival.hour,
                "booking_lead_time_hours": float(np.clip(lead_time_hours, 1, 120)),
                "missing_documents_count": missing_documents,
                "weather_severity": weather_severity,
                "traffic_index": traffic_index if traffic_index is not None else traffic_index_for_hour(arrival.hour),
                "vessel_delay_flag": int(vessel_delay),
                "carrier_past_reliability_score": carrier_reliability,
                "carrier_hist_no_show_rate": hist.get("carrier_hist_no_show_rate", DEFAULT_HIST_NO_SHOW_RATE),
                "carrier_hist_avg_lateness_min": hist.get(
                    "carrier_hist_avg_lateness_min", DEFAULT_HIST_AVG_LATENESS_MIN
                ),
            }
        ]
    )


def predict_risk(row: pd.DataFrame, top_k: int = 3) -> dict:
    """Return outcome probabilities and the top SHAP drivers of no-show risk."""
    if _artifact is None:
        raise RuntimeError("No-show model not loaded yet")

    pipe, classes = _artifact["pipeline"], _artifact["classes"]
    proba = pipe.predict_proba(row[_artifact["features"]])[0]
    probs = {c: float(p) for c, p in zip(classes, proba)}

    x = pipe.named_steps["preprocess"].transform(row[_artifact["features"]])
    sv = _explainer.shap_values(x)
    sv = np.stack(sv, axis=-1) if isinstance(sv, list) else np.asarray(sv)
    contrib = sv[0, :, classes.index("no_show")]

    order = np.argsort(-np.abs(contrib))[:top_k]
    drivers = [
        {
            "feature": _feature_names[i],
            "label": _label(_feature_names[i], row.iloc[0]),
            "effect": "raises" if contrib[i] > 0 else "lowers",
            "shap": round(float(contrib[i]), 3),
        }
        for i in order
    ]
    return {
        "p_on_time": round(probs["on_time"], 4),
        "p_late": round(probs["late"], 4),
        "p_no_show": round(probs["no_show"], 4),
        "drivers": drivers,
        "summary": explain_sentence(round(probs["no_show"], 4), drivers),
    }


def explain_sentence(p_no_show: float, drivers: list[dict]) -> str:
    raising = [d["label"] for d in drivers if d["effect"] == "raises"]
    lowering = [d["label"] for d in drivers if d["effect"] == "lowers"]
    parts = [f"No-show risk {p_no_show:.0%}"]
    if raising:
        parts.append("raised by " + ", ".join(raising))
    if lowering:
        parts.append("lowered by " + ", ".join(lowering))
    return "; ".join(parts) + "."
