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


# ---- bookings whose documents have not been checked yet ---------------------------------------

# Typical document situation in the training data. Before OCR has verified a booking's documents the
# customs risk and missing-document count are unknown, so the prediction is the average over these.
DOC_PRIOR_CUSTOMS = {"low": 0.72, "medium": 0.20, "high": 0.08}
DOC_PRIOR_MISSING = {0: 0.75, 1: 0.15, 2: 0.07, 3: 0.03}
MODEL_MAX_MISSING = 3  # the models were trained on 0-3 missing documents


def document_scenarios(customs: str | None, missing: int | None) -> list[tuple[str, int, float]]:
    """(customs risk, missing documents, probability) for every case still possible."""
    customs_options = {customs: 1.0} if customs else DOC_PRIOR_CUSTOMS
    missing_options = {min(missing, MODEL_MAX_MISSING): 1.0} if missing is not None else DOC_PRIOR_MISSING
    return [(c, m, pc * pm) for c, pc in customs_options.items() for m, pm in missing_options.items()]


# Typical conditions in the training data, used when weather or vessel delay cannot be established.
VESSEL_PRIOR_DELAYED = 0.12
WEATHER_PRIOR_MONSOON = {0: 0.40, 1: 0.30, 2: 0.20, 3: 0.10}  # May, Jun, Oct, Nov, Dec
WEATHER_PRIOR_DRY = {0: 0.70, 1: 0.20, 2: 0.07, 3: 0.03}
MONSOON_MONTHS = {5, 6, 10, 11, 12}


def weather_scenarios(weather: int | None, month: int) -> list[tuple[int, float]]:
    if weather is not None:
        return [(weather, 1.0)]
    return list((WEATHER_PRIOR_MONSOON if month in MONSOON_MONTHS else WEATHER_PRIOR_DRY).items())


def vessel_scenarios(vessel_delay: bool | None) -> list[tuple[bool, float]]:
    if vessel_delay is not None:
        return [(vessel_delay, 1.0)]
    return [(False, 1 - VESSEL_PRIOR_DELAYED), (True, VESSEL_PRIOR_DELAYED)]


def predict_risk_for_documents(
    customs: str | None,
    missing: int | None,
    weather_severity: int | None = 0,
    vessel_delay: bool | None = False,
    **row_args,
) -> dict:
    """Risk where any of customs risk, missing documents, weather and vessel delay may be unknown (None).

    Everything known -> identical to predict_risk on that row. Otherwise the outcome probabilities are the
    weighted average over the cases still possible (typical situation from the training data), and the SHAP
    drivers come from the most likely case with the assumed factors left out, so a guess is never shown as
    a reason."""
    month = row_args["arrival"].month
    cases = [
        (c, m, w, v, pc * pm * pw * pv)
        for c, pc in ({customs: 1.0} if customs else DOC_PRIOR_CUSTOMS).items()
        for m, pm in ({min(missing, MODEL_MAX_MISSING): 1.0} if missing is not None else DOC_PRIOR_MISSING).items()
        for w, pw in weather_scenarios(weather_severity, month)
        for v, pv in vessel_scenarios(vessel_delay)
    ]
    rows = [
        build_row(customs_risk_flag=c, missing_documents=m, weather_severity=w, vessel_delay=v, **row_args)
        for c, m, w, v, _ in cases
    ]
    weights = np.array([case[4] for case in cases])
    weights = weights / weights.sum()
    modal = int(np.argmax(weights))

    unknown = {
        "customs": customs is None,
        "missing": missing is None,
        "weather": weather_severity is None,
        "vessel": vessel_delay is None,
    }
    out = predict_risk(rows[modal], top_k=10 if len(rows) > 1 else 3)
    if len(rows) > 1:
        assumed = (
            (["missing_documents_count"] if unknown["missing"] else [])
            + (["customs_risk_flag_"] if unknown["customs"] else [])
            + (["weather_severity"] if unknown["weather"] else [])
            + (["vessel_delay_flag"] if unknown["vessel"] else [])
        )
        out["drivers"] = [d for d in out["drivers"] if not any(d["feature"].startswith(a) for a in assumed)][:3]
        frame = pd.concat(rows, ignore_index=True)
        proba = _artifact["pipeline"].predict_proba(frame[_artifact["features"]])
        avg = (proba * weights[:, None]).sum(axis=0)
        by_class = dict(zip(_artifact["classes"], avg))
        out["p_on_time"] = round(float(by_class["on_time"]), 4)
        out["p_late"] = round(float(by_class["late"]), 4)
        out["p_no_show"] = round(float(by_class["no_show"]), 4)
        notes = []
        if unknown["customs"] or unknown["missing"]:
            notes.append("documents not checked yet")
        if unknown["vessel"]:
            notes.append("vessel delay not known yet")
        if unknown["weather"]:
            notes.append("weather forecast unavailable")
        out["summary"] = (
            explain_sentence(out["p_no_show"], out["drivers"]) + " " + notes[0].capitalize()
            + "".join(f", {n}" for n in notes[1:]) + ": typical situation assumed."
        )
    out["documents_known"] = not unknown["customs"] and not unknown["missing"]
    out["customs_known"] = not unknown["customs"]
    out["missing_known"] = not unknown["missing"]
    out["weather_known"] = not unknown["weather"]
    out["vessel_known"] = not unknown["vessel"]
    return out


# ---- carrier profiles (reliability and history come from the model, not from the user) --------------

DEFAULT_RELIABILITY = 0.75  # training-data mean, for a carrier the model has never seen


def carrier_profile(carrier: str) -> dict | None:
    hist = _artifact["carrier_history"].get(carrier)
    if hist is None:
        return None
    return {
        "carrier": carrier,
        "reliability": hist.get("reliability", DEFAULT_RELIABILITY),
        "past_no_show_rate": hist["carrier_hist_no_show_rate"],
        "avg_lateness_min": hist["carrier_hist_avg_lateness_min"],
    }


def carrier_profiles() -> list[dict]:
    return [carrier_profile(c) for c in sorted(_artifact["carrier_history"])]
