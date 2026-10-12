"""
No-show / late-arrival risk model (Model 2, Component 4 technical plan).

For each booking, predicts the probability of three outcomes:
    on_time | late | no_show

Logistic Regression (class_weight="balanced") is the baseline; XGBoost is the
accuracy model. No-shows are rare (~8%), so both use class balancing, and
evaluation reports per-class precision / recall / F1 plus ROC-AUC with attention
on recall for the no_show class (a missed no-show wastes gate capacity).

The split is chronological (never shuffled): the last 20% of bookings by booked
slot are held out. The best model by macro ROC-AUC is saved together with a SHAP
importance summary.

Usage: python src/train_noshow_model.py   (run generate_booking_data.py first)
"""

import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "raw" / "gate_booking_noshow_dataset_2024_2025.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

# Class order is fixed so integer labels map the same way in training and serving.
CLASSES = ["late", "no_show", "on_time"]
CLASS_TO_INT = {c: i for i, c in enumerate(CLASSES)}

CATEGORICAL_FEATURES = ["day_of_week", "container_type", "cargo_category", "customs_risk_flag"]
NUMERIC_FEATURES = [
    "booked_hour",
    "booking_lead_time_hours",
    "missing_documents_count",
    "weather_severity",
    "traffic_index",
    "vessel_delay_flag",
    "carrier_past_reliability_score",
    "carrier_hist_no_show_rate",
    "carrier_hist_avg_lateness_min",
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

TEST_FRACTION = 0.2


def load_split():
    df = pd.read_csv(DATA_PATH, parse_dates=["booked_slot"]).sort_values("booked_slot").reset_index(drop=True)
    split = int(len(df) * (1 - TEST_FRACTION))
    return df.iloc[:split], df.iloc[split:]


def build_pipeline(model, scale: bool) -> Pipeline:
    numeric = StandardScaler() if scale else "passthrough"
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", numeric, NUMERIC_FEATURES),
        ]
    )
    return Pipeline([("preprocess", pre), ("model", model)])


def evaluate(y_true, proba) -> dict:
    pred = proba.argmax(axis=1)
    report = classification_report(
        y_true, pred, labels=range(len(CLASSES)), target_names=CLASSES, output_dict=True, zero_division=0
    )
    ns = CLASS_TO_INT["no_show"]
    per_class = {
        c: {k: round(report[c][k], 3) for k in ("precision", "recall", "f1-score")} for c in CLASSES
    }
    return {
        "per_class": per_class,
        "macro_f1": round(report["macro avg"]["f1-score"], 3),
        "accuracy": round(report["accuracy"], 3),
        "roc_auc_macro_ovr": round(float(roc_auc_score(y_true, proba, multi_class="ovr", average="macro")), 3),
        "roc_auc_no_show": round(float(roc_auc_score((y_true == ns).astype(int), proba[:, ns])), 3),
        "pr_auc_no_show": round(float(average_precision_score((y_true == ns).astype(int), proba[:, ns])), 3),
        "confusion_matrix": confusion_matrix(y_true, pred, labels=range(len(CLASSES))).tolist(),
    }


def make_models():
    return {
        "logistic_regression": lambda: build_pipeline(
            LogisticRegression(class_weight="balanced", max_iter=2000), scale=True
        ),
        "xgboost": lambda: build_pipeline(
            XGBClassifier(
                objective="multi:softprob",
                n_estimators=150,
                max_depth=3,
                learning_rate=0.05,
                min_child_weight=20,
                reg_lambda=10,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
            ),
            scale=False,
        ),
    }


def fit(name, pipe, X, y, balanced: bool):
    kwargs = {}
    if name == "xgboost" and balanced:
        kwargs["model__sample_weight"] = compute_sample_weight("balanced", y)
    pipe.fit(X, y, **kwargs)
    return pipe


def make_serving(name, pipe):
    """Probabilities used by the overbooking layer must be calibrated, so the
    serving model is the chosen family trained WITHOUT class balancing."""
    return fit(name, make_models()[name](), X_FULL, Y_FULL, balanced=False)


def calibration(y_true, proba) -> dict:
    ns = CLASS_TO_INT["no_show"]
    is_ns = (y_true == ns).astype(int)
    return {
        "mean_predicted_no_show": round(float(proba[:, ns].mean()), 4),
        "observed_no_show_rate": round(float(is_ns.mean()), 4),
        "brier_no_show": round(float(np.mean((proba[:, ns] - is_ns) ** 2)), 4),
        "brier_no_show_constant_baseline": round(float(np.mean((is_ns.mean() - is_ns) ** 2)), 4),
    }


def main():
    global X_FULL, Y_FULL
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    train, test = load_split()
    X_FULL, X_test = train[FEATURES], test[FEATURES]
    Y_FULL = train["status"].map(CLASS_TO_INT).to_numpy()
    y_test = test["status"].map(CLASS_TO_INT).to_numpy()
    print(f"Train {len(train)} rows | Test {len(test)} rows")
    print("Test class mix:", test["status"].value_counts(normalize=True).round(3).to_dict())

    # Model selection on a chronological validation slice carved from the training
    # period, so the held-out test period is only used for the final report.
    cut = int(len(train) * 0.85)
    X_fit, X_val = X_FULL.iloc[:cut], X_FULL.iloc[cut:]
    y_fit, y_val = Y_FULL[:cut], Y_FULL[cut:]
    val_auc = {}
    for name, factory in make_models().items():
        pipe = fit(name, factory(), X_fit, y_fit, balanced=True)
        val_auc[name] = float(roc_auc_score(y_val, pipe.predict_proba(X_val), multi_class="ovr", average="macro"))
    best = max(val_auc, key=val_auc.get)
    print("Validation macro ROC-AUC:", {k: round(v, 3) for k, v in val_auc.items()}, "-> best:", best)

    # Reported test metrics: class-balanced versions of both models (recall focus).
    results = {}
    for name, factory in make_models().items():
        pipe = fit(name, factory(), X_FULL, Y_FULL, balanced=True)
        results[name] = evaluate(y_test, pipe.predict_proba(X_test))
        ns = results[name]["per_class"]["no_show"]
        print(
            f"{name}: macro-F1 {results[name]['macro_f1']} | AUC {results[name]['roc_auc_macro_ovr']} | "
            f"no_show P {ns['precision']} R {ns['recall']} F1 {ns['f1-score']}"
        )

    # Serving model: calibrated probabilities for the decision layer.
    serving = make_serving(best, None)
    serving_proba = serving.predict_proba(X_test)
    serving_eval = evaluate(y_test, serving_proba)
    serving_cal = calibration(y_test, serving_proba)
    print("Serving model (unweighted, calibrated):", serving_cal)

    # --- SHAP importance of the serving model for the no_show class
    pre, model = serving.named_steps["preprocess"], serving.named_steps["model"]
    names = [n.split("__", 1)[1] for n in pre.get_feature_names_out()]
    background = pre.transform(X_FULL.sample(200, random_state=0))
    sample = pre.transform(X_test.sample(min(1000, len(X_test)), random_state=0))
    explainer = shap.TreeExplainer(model) if best == "xgboost" else shap.LinearExplainer(model, background)
    sv = explainer.shap_values(sample)
    sv = np.stack(sv, axis=-1) if isinstance(sv, list) else sv
    ns_idx = CLASS_TO_INT["no_show"]
    mean_abs = np.abs(sv[:, :, ns_idx]).mean(axis=0)
    importance = (
        pd.DataFrame({"feature": names, "mean_abs_shap_no_show": mean_abs.round(5)})
        .sort_values("mean_abs_shap_no_show", ascending=False)
        .reset_index(drop=True)
    )
    importance.to_json(REPORT_DIR / "noshow_shap_importance.json", orient="records", indent=2)

    top = importance.head(10).iloc[::-1]
    plt.figure(figsize=(7, 4))
    plt.barh(top["feature"], top["mean_abs_shap_no_show"], color="#123a5c")
    plt.xlabel("mean |SHAP value| (no_show class)")
    plt.title("What drives predicted no-show risk")
    plt.tight_layout()
    plt.savefig(REPORT_DIR / "noshow_shap_importance.png", dpi=130)
    plt.close()
    print("\nTop SHAP drivers of no-show risk:")
    print(importance.head(8).to_string(index=False))

    joblib.dump(
        {
            "pipeline": serving,
            "classes": CLASSES,
            "features": FEATURES,
            "family": best,
            "background": background[:100],
        },
        MODEL_DIR / "noshow_model.joblib",
    )
    with open(REPORT_DIR / "noshow_model_metrics.json", "w") as f:
        json.dump(
            {
                "serving_model": best,
                "selection_validation_roc_auc": {k: round(v, 3) for k, v in val_auc.items()},
                "classes": CLASSES,
                "train_rows": len(train),
                "test_rows": len(test),
                "test_class_share": test["status"].value_counts(normalize=True).round(3).to_dict(),
                "class_balanced_test_metrics": results,
                "serving_model_test_metrics": serving_eval,
                "serving_model_calibration": serving_cal,
            },
            f,
            indent=2,
        )
    print(f"\nSaved model and reports to {MODEL_DIR} / {REPORT_DIR}")


if __name__ == "__main__":
    main()
