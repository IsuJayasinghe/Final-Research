"""
End-to-end evaluation of the no-show-aware appointment framework (technical plan,
section 7): average gate waiting time, gate turn time, appointment adherence and
throughput, against baselines.

Method: a day-by-day discrete-event simulation of the gate.
  * Demand: every simulated day draws booking requests with the real hourly demand
    profile. Booking attributes AND their realised outcome (on time / late /
    no-show, and lateness) are sampled from the HELD-OUT test period of the booking
    dataset - data Model 2 never saw during training.
  * Service: each arriving truck is served by the first free of 6 lanes (FIFO);
    service time is drawn from real clearance durations for the same container type
    and customs-risk class.
  * Three policies see identical demand and identical outcomes (paired comparison):
      1. static_tas          fixed capacity per hourly slot, no overbooking
      2. blind_overbooking   accepts up to +20% over capacity with no risk model
      3. framework           Model 2 risk -> expected-arrivals rule + congestion-aware
                             slot choice (backend/gate/scheduler.decide_slot)

Assumptions (also written into the report): synthetic booking data; a single
shared queue for 6 lanes; no overnight carry-over; hourly slots; slot capacity
and demand level are set so peak hours are over-subscribed.

Usage: python src/evaluate_framework.py   (needs the trained models and datasets)
"""

import heapq
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parents[1] / "backend" / "gate"))

import ml_models  # noqa: E402  (backend module: congestion forecast used for slot cost)
import scheduler  # noqa: E402  (backend module: the decision layer under test)
from generate_booking_data import HOURLY_DEMAND  # noqa: E402
from train_noshow_model import CLASS_TO_INT, FEATURES, load_split  # noqa: E402

REPORT_DIR = ROOT / "reports"
CLEARANCE_PATH = ROOT / "data" / "raw" / "gate_document_clearance_dataset_2024_2025.csv"

DAYS = 60
REQUESTS_PER_DAY = 300
LANES = 6
SLOT_CAPACITY = 16  # bookable trucks per hourly slot (gate can clear ~19/h on average)
MAX_OVERBOOK_SHARE = 0.25  # framework: hard cap above capacity, as a share of capacity
BLIND_OVERBOOK_FACTOR = 1.2
SEED = 7
SENSITIVITY_CAPACITIES = (12, 18, 20)
SENSITIVITY_DAYS = 30
SHIFT_ORDER = [0, 1, -1, 2, -2, 3, -3]


def build_world():
    _, test = load_split()
    art = joblib.load(ROOT / "models" / "noshow_model.joblib")
    ns = CLASS_TO_INT["no_show"]
    test = test.copy()
    test["p_no_show"] = art["pipeline"].predict_proba(test[FEATURES])[:, ns]
    by_hour = {h: g.reset_index(drop=True) for h, g in test.groupby("booked_hour")}

    clr = pd.read_csv(CLEARANCE_PATH)
    pool = {k: g["clearance_duration_minutes"].to_numpy() for k, g in clr.groupby(["container_type", "customs_risk_flag"])}
    # a few type/risk combinations never occur in the clearance data; fall back to the type's own durations
    for ctype, g in clr.groupby("container_type"):
        for risk in ("low", "medium", "high"):
            pool.setdefault((ctype, risk), g["clearance_duration_minutes"].to_numpy())
    return by_hour, pool


def make_day(rng, by_hour, pool):
    profile = HOURLY_DEMAND / HOURLY_DEMAND.sum()
    hours = rng.choice(24, size=REQUESTS_PER_DAY, p=profile)
    reqs = []
    for i, h in enumerate(hours):
        g = by_hour[int(h)]
        row = g.iloc[int(rng.integers(len(g)))]
        service = float(rng.choice(pool[(row["container_type"], row["customs_risk_flag"])]))
        reqs.append(
            {
                "id": i,
                "hour": int(h),
                "p_no_show": float(row["p_no_show"]),
                "status": row["status"],
                "lateness": float(row["actual_lateness_minutes"]) if row["status"] == "late" else 0.0,
                "service": service,
                "jitter": float(rng.uniform(0, 60)),  # minute within the slot a truck aims for
            }
        )
    order = rng.permutation(REQUESTS_PER_DAY)  # requests reach the booking system in random order
    return [reqs[i] for i in order]


# ---- policies: each returns {request id: assigned hour or None} -------------------------

def static_policy(reqs, limit):
    count, out = defaultdict(int), {}
    for r in reqs:
        out[r["id"]] = None
        for d in SHIFT_ORDER:
            s = r["hour"] + d
            if 0 <= s <= 23 and count[s] < limit:
                count[s] += 1
                out[r["id"]] = s
                break
    return out


def framework_policy(reqs, day: datetime, wait_fn, capacity: int, max_over: int):
    states, out = [], {}
    for r in reqs:
        requested = day + timedelta(hours=r["hour"])
        d = scheduler.decide_slot(
            requested, r["p_no_show"], states, day, wait_fn, capacity=capacity, max_overbook=max_over
        )
        if d.slot is not None and d.slot < day + timedelta(days=1):
            states.append(scheduler.BookingState(r["id"], requested, d.slot, r["p_no_show"], "PENDING"))
            out[r["id"]] = d.slot.hour
        else:
            out[r["id"]] = None
    return out


# ---- gate simulation -------------------------------------------------------------------

def run_gate(reqs, assignment):
    """Serve arriving trucks with LANES parallel servers; return per-day metrics."""
    arrivals = []
    for r in reqs:
        slot = assignment[r["id"]]
        if slot is None or r["status"] == "no_show":
            continue
        t = slot * 60 + r["jitter"] + (r["lateness"] if r["status"] == "late" else 0.0)
        arrivals.append((t, slot, r["service"]))
    arrivals.sort()

    lanes = [0.0] * LANES
    heapq.heapify(lanes)
    waits, turns, in_slot = [], [], 0
    for t, slot, service in arrivals:
        free = heapq.heappop(lanes)
        start = max(t, free)
        heapq.heappush(lanes, start + service)
        waits.append(start - t)
        turns.append(start - t + service)
        in_slot += slot * 60 <= t < (slot + 1) * 60
    accepted = sum(1 for v in assignment.values() if v is not None)
    return {
        "accepted": accepted,
        "rejected": len(assignment) - accepted,
        "served": len(arrivals),
        "avg_wait_min": float(np.mean(waits)) if waits else 0.0,
        "p90_wait_min": float(np.percentile(waits, 90)) if waits else 0.0,
        "avg_turn_min": float(np.mean(turns)) if turns else 0.0,
        "adherence": in_slot / len(arrivals) if arrivals else 0.0,
    }


def summarise(days: list[dict]) -> dict:
    out = {}
    for k in days[0]:
        v = np.array([d[k] for d in days])
        out[k] = {"mean": round(float(v.mean()), 3), "ci95": round(float(1.96 * v.std(ddof=1) / np.sqrt(len(v))), 3)}
    return out


def run_scenario(capacity: int, days: int, by_hour, pool, wait_fn, seed: int) -> dict:
    max_over = max(1, round(MAX_OVERBOOK_SHARE * capacity))
    rng = np.random.default_rng(seed)
    results = {"static_tas": [], "blind_overbooking": [], "framework": []}
    base_day = datetime(2030, 1, 7)
    for d in range(days):
        day = base_day + timedelta(days=d)
        reqs = make_day(rng, by_hour, pool)
        assignments = {
            "static_tas": static_policy(reqs, capacity),
            "blind_overbooking": static_policy(reqs, int(capacity * BLIND_OVERBOOK_FACTOR)),
            "framework": framework_policy(reqs, day, wait_fn, capacity, max_over),
        }
        for name, assignment in assignments.items():
            results[name].append(run_gate(reqs, assignment))
    return results


def paired(results, metric, base="static_tas"):
    diff = np.array([f[metric] - s[metric] for f, s in zip(results["framework"], results[base])])
    return {"mean": round(float(diff.mean()), 3), "ci95": round(float(1.96 * diff.std(ddof=1) / np.sqrt(len(diff))), 3)}


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ml_models.load_models()
    by_hour, pool = build_world()

    def wait_fn(slot):
        return ml_models.estimate_wait_minutes(min(ml_models.get_all_lane_forecasts(slot).values()))

    # headline scenario
    print(f"Headline scenario: capacity {SLOT_CAPACITY}/slot, {DAYS} days")
    results = run_scenario(SLOT_CAPACITY, DAYS, by_hour, pool, wait_fn, SEED)
    summary = {name: summarise(days) for name, days in results.items()}

    # sensitivity: how the picture changes as slots are tighter or looser relative to gate capacity
    sensitivity = {}
    for cap in SENSITIVITY_CAPACITIES:
        print(f"Sensitivity: capacity {cap}/slot, {SENSITIVITY_DAYS} days")
        r = run_scenario(cap, SENSITIVITY_DAYS, by_hour, pool, wait_fn, SEED + cap)
        sensitivity[str(cap)] = {
            "static_tas": {k: round(float(np.mean([d[k] for d in r["static_tas"]])), 2) for k in ("served", "avg_wait_min", "p90_wait_min")},
            "blind_overbooking": {k: round(float(np.mean([d[k] for d in r["blind_overbooking"]])), 2) for k in ("served", "avg_wait_min", "p90_wait_min")},
            "framework": {k: round(float(np.mean([d[k] for d in r["framework"]])), 2) for k in ("served", "avg_wait_min", "p90_wait_min")},
            "framework_vs_static_served": paired(r, "served"),
            "framework_vs_static_wait_min": paired(r, "avg_wait_min"),
        }

    report = {
        "setup": {
            "days": DAYS,
            "requests_per_day": REQUESTS_PER_DAY,
            "lanes": LANES,
            "slot_capacity": SLOT_CAPACITY,
            "framework_max_overbook_share": MAX_OVERBOOK_SHARE,
            "blind_overbook_factor": BLIND_OVERBOOK_FACTOR,
            "seed": SEED,
        },
        "assumptions": [
            "Booking data is synthetic; outcomes are sampled from the held-out test period Model 2 never trained on.",
            "Six lanes share one FIFO queue; service times come from real clearance durations by container type and customs risk.",
            "Hourly slots, no overnight carry-over; peak hours are over-subscribed by design (300 requests/day vs 16 per slot).",
            "Re-optimization after disruptions is verified by tests/demo, not included in this steady-state comparison.",
            "Gate service capacity is about 19 trucks/hour, so with 16 bookings/slot the gate is not saturated; "
            "the sensitivity table shows how results change when slots are tighter or looser.",
        ],
        "results_per_day": summary,
        "framework_vs_static_paired": {m: paired(results, m) for m in ("served", "accepted", "avg_wait_min", "avg_turn_min", "adherence")},
        "framework_vs_blind_paired": {m: paired(results, m, "blind_overbooking") for m in ("served", "avg_wait_min", "avg_turn_min")},
        "sensitivity_by_slot_capacity": sensitivity,
    }
    with open(REPORT_DIR / "framework_evaluation.json", "w") as f:
        json.dump(report, f, indent=2)

    names = ["static_tas", "blind_overbooking", "framework"]
    labels = ["Static TAS", "Blind +20%", "Framework"]
    colors = ["#9aa5b1", "#d9822b", "#123a5c"]
    metrics = [("served", "Trucks served / day"), ("avg_wait_min", "Avg gate wait (min)"), ("avg_turn_min", "Avg turn time (min)"), ("adherence", "Slot adherence")]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.2))
    for ax, (m, title) in zip(axes, metrics):
        vals = [summary[n][m]["mean"] for n in names]
        errs = [summary[n][m]["ci95"] for n in names]
        ax.bar(labels, vals, yerr=errs, color=colors, capsize=3)
        ax.set_title(title, fontsize=10)
        ax.tick_params(axis="x", labelsize=8)
    plt.tight_layout()
    plt.savefig(REPORT_DIR / "framework_evaluation.png", dpi=130)
    plt.close()

    print("\nMean per day (95% CI), headline scenario:")
    for n in names:
        s_ = summary[n]
        print(
            f"{n:18s} accepted {s_['accepted']['mean']:.1f} | served {s_['served']['mean']:.1f} | wait {s_['avg_wait_min']['mean']:.1f} "
            f"| p90 {s_['p90_wait_min']['mean']:.1f} | turn {s_['avg_turn_min']['mean']:.1f} | adherence {s_['adherence']['mean']:.3f}"
        )
    print("Framework vs static (paired):", json.dumps(report["framework_vs_static_paired"]))
    print("Framework vs blind  (paired):", json.dumps(report["framework_vs_blind_paired"]))
    print("Sensitivity:", json.dumps(sensitivity, indent=1))


if __name__ == "__main__":
    main()
