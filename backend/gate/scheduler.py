"""
No-show-aware overbooking and slot re-optimization (decision layer of Component 4).

Combines the two models:
  Model 1 (congestion forecast)  -> expected gate wait for each hourly slot
  Model 2 (no-show risk)         -> expected arrivals of each booking = 1 - p_no_show

Overbooking rule (technical plan, section 5.3): a slot may take extra bookings as
long as the EXPECTED number of arrivals stays within gate capacity, with a hard
cap on how many bookings above capacity are allowed:

    expected_arrivals = sum(1 - p_no_show for booking in slot)
    accept new booking if expected_arrivals + (1 - p_new) <= capacity
                      and bookings_in_slot + 1 <= capacity + MAX_OVERBOOK

Re-optimization: when a disruption arrives (vessel delay, queue spike), only the
UNCONFIRMED future bookings are reshuffled, by solving a small integer program
(PuLP / CBC) that minimizes expected wait + deviation from the requested time,
subject to the same expected-arrival capacity per slot. Confirmed bookings stay
fixed. Everything here is pure (no I/O) so it can be unit-tested and simulated.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

import pulp

SLOT_CAPACITY = int(os.environ.get("GATE_SLOT_CAPACITY", 6))  # bookable trucks per hourly slot
MAX_OVERBOOK = int(os.environ.get("GATE_MAX_OVERBOOK", 2))  # bookings allowed above capacity
SEARCH_RADIUS_HOURS = 3  # a booking may move this many hours either side of the request
DEVIATION_PENALTY_MIN_PER_HOUR = 12.0  # cost of being moved away from the requested hour
MOVE_PENALTY_MIN = 4.0  # stability: prefer not to move a booking at all
UNASSIGNED_COST = 1000.0

ACTIVE_STATUSES = ("PENDING", "CONFIRMED", "ARRIVED")

WaitFn = Callable[[datetime], float]


@dataclass
class BookingState:
    id: int
    requested_slot: datetime
    assigned_slot: datetime | None
    p_no_show: float
    status: str = "PENDING"  # PENDING (unconfirmed) | CONFIRMED | WAITLISTED | CANCELLED


@dataclass
class Disruption:
    """A change in conditions that raises forecast congestion for a window of slots."""

    kind: str = "none"  # "vessel_delay" | "queue_spike" | "none"
    vessel_delay_hours: float = 0.0
    queue_spike_pct: float = 0.0
    start: datetime = field(default_factory=datetime.now)
    window_hours: int = 4
    lane: int | None = None  # None = the whole gate; a number = only that lane is affected

    def uplift(self, slot: datetime) -> float:
        """Fractional increase in forecast congestion for this slot (0.18 = +18%)."""
        if not (self.start.replace(minute=0, second=0, microsecond=0) <= slot < self.start + timedelta(hours=self.window_hours)):
            return 0.0
        vessel = min(0.6, 0.15 * self.vessel_delay_hours)
        return vessel + self.queue_spike_pct / 100.0


@dataclass
class Decision:
    slot: datetime | None
    overbooked: bool
    status: str  # PENDING | WAITLISTED
    reason: str
    expected_before: float = 0.0
    expected_after: float = 0.0
    bookings_after: int = 0
    candidates: list[dict] = field(default_factory=list)


@dataclass
class Move:
    booking_id: int
    old_slot: datetime | None
    new_slot: datetime | None
    old_cost: float
    new_cost: float


def hour_floor(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def candidate_slots(requested: datetime, earliest: datetime) -> list[datetime]:
    base = hour_floor(requested)
    slots = [base + timedelta(hours=d) for d in range(-SEARCH_RADIUS_HOURS, SEARCH_RADIUS_HOURS + 1)]
    return [s for s in slots if s >= hour_floor(earliest)]


def slot_load(bookings: list[BookingState], slot: datetime, exclude_id: int | None = None) -> tuple[int, float]:
    """(booking count, expected arrivals) for active bookings assigned to a slot."""
    active = [
        b for b in bookings
        if b.status in ACTIVE_STATUSES and b.assigned_slot == slot and b.id != exclude_id
    ]
    return len(active), sum(1.0 - b.p_no_show for b in active)


def slot_cost(slot: datetime, requested: datetime, wait_fn: WaitFn) -> float:
    return wait_fn(slot) + DEVIATION_PENALTY_MIN_PER_HOUR * abs((slot - hour_floor(requested)).total_seconds() / 3600)


def decide_slot(
    requested: datetime,
    p_no_show: float,
    bookings: list[BookingState],
    earliest: datetime,
    wait_fn: WaitFn,
    capacity: int = SLOT_CAPACITY,
    max_overbook: int = MAX_OVERBOOK,
) -> Decision:
    """Pick the cheapest slot near the request that satisfies the overbooking rule."""
    expected_new = 1.0 - p_no_show
    evaluated, feasible = [], []
    for s in candidate_slots(requested, earliest):
        count, expected = slot_load(bookings, s)
        ok = (expected + expected_new <= capacity) and (count + 1 <= capacity + max_overbook)
        cost = slot_cost(s, requested, wait_fn)
        row = {
            "slot": s.isoformat(timespec="minutes"),
            "bookings": count,
            "expected_arrivals": round(expected, 2),
            "forecast_wait_min": round(wait_fn(s), 1),
            "cost": round(cost, 1),
            "feasible": ok,
        }
        evaluated.append(row)
        if ok:
            feasible.append((cost, abs((s - hour_floor(requested)).total_seconds()), s, count, expected))

    if not feasible:
        return Decision(
            None, False, "WAITLISTED",
            "All nearby slots are full (expected arrivals at capacity); booking waitlisted.",
            candidates=evaluated,
        )

    _, _, slot, count, expected = min(feasible)
    overbooked = count + 1 > capacity
    req = hour_floor(requested)
    if slot == req:
        where = "requested slot"
    else:
        req_row = next((r for r in evaluated if r["slot"] == req.isoformat(timespec="minutes")), None)
        if req_row is not None and not req_row["feasible"]:
            why = "the requested slot is at expected capacity"
        else:
            why = f"forecast gate wait {wait_fn(slot):.0f} min vs {wait_fn(req):.0f} min at the requested time"
        where = f"slot {slot:%H:%M} instead of requested {req:%H:%M} ({why})"
    if overbooked:
        reason = (
            f"Overbooked {where}: {count} booked vs capacity {capacity}, but expected arrivals "
            f"{expected + expected_new:.1f} stay within capacity because of predicted no-shows."
        )
    else:
        reason = f"Assigned {where}; expected arrivals {expected + expected_new:.1f} of capacity {capacity}."
    return Decision(
        slot, overbooked, "PENDING", reason,
        expected_before=round(expected, 2),
        expected_after=round(expected + expected_new, 2),
        bookings_after=count + 1,
        candidates=evaluated,
    )


def reoptimize(
    unconfirmed: list[BookingState],
    confirmed: list[BookingState],
    earliest: datetime,
    wait_fn: WaitFn,
    capacity: int = SLOT_CAPACITY,
    max_overbook: int = MAX_OVERBOOK,
) -> list[Move]:
    """Reassign UNCONFIRMED bookings by integer programming; confirmed ones stay fixed.

    Returns one Move per unconfirmed booking (old == new when nothing changes).
    """
    if not unconfirmed:
        return []

    cands = {b.id: candidate_slots(b.requested_slot, earliest) for b in unconfirmed}
    all_slots = sorted({s for slots in cands.values() for s in slots})
    fixed = {s: slot_load(confirmed, s) for s in all_slots}

    prob = pulp.LpProblem("gate_slot_reoptimization", pulp.LpMinimize)
    x = {
        (b.id, s): pulp.LpVariable(f"x_{b.id}_{int(s.timestamp())}", cat="Binary")
        for b in unconfirmed for s in cands[b.id]
    }
    u = {b.id: pulp.LpVariable(f"u_{b.id}", cat="Binary") for b in unconfirmed}

    def cost(b: BookingState, s: datetime) -> float:
        c = slot_cost(s, b.requested_slot, wait_fn)
        return c + (MOVE_PENALTY_MIN if s != b.assigned_slot else 0.0)

    prob += pulp.lpSum(x[(b.id, s)] * cost(b, s) for b in unconfirmed for s in cands[b.id]) + pulp.lpSum(
        u[b.id] * UNASSIGNED_COST for b in unconfirmed
    )
    for b in unconfirmed:
        prob += pulp.lpSum(x[(b.id, s)] for s in cands[b.id]) + u[b.id] == 1
    for s in all_slots:
        members = [b for b in unconfirmed if s in cands[b.id]]
        if not members:
            continue
        fixed_count, fixed_exp = fixed[s]
        prob += pulp.lpSum((1.0 - b.p_no_show) * x[(b.id, s)] for b in members) <= max(0.0, capacity - fixed_exp)
        prob += pulp.lpSum(x[(b.id, s)] for b in members) <= max(0, capacity + max_overbook - fixed_count)

    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=10))
    if pulp.LpStatus[prob.status] != "Optimal":
        raise RuntimeError(f"Re-optimization failed: {pulp.LpStatus[prob.status]}")

    moves = []
    for b in unconfirmed:
        new_slot = next((s for s in cands[b.id] if x[(b.id, s)].value() and x[(b.id, s)].value() > 0.5), None)
        old_cost = slot_cost(b.assigned_slot, b.requested_slot, wait_fn) if b.assigned_slot else UNASSIGNED_COST
        new_cost = slot_cost(new_slot, b.requested_slot, wait_fn) if new_slot else UNASSIGNED_COST
        moves.append(Move(b.id, b.assigned_slot, new_slot, round(old_cost, 1), round(new_cost, 1)))
    return moves


def explain_move(
    move: Move,
    base_wait_fn: WaitFn,
    wait_fn: WaitFn,
    disruption: Disruption,
    risk_summary: str | None = None,
) -> list[str]:
    """Plain-language reasons for a reassignment (the explainability requirement)."""
    reasons = []
    if move.old_slot is not None:
        base, now_ = base_wait_fn(move.old_slot), wait_fn(move.old_slot)
        if base > 0 and now_ > base:
            pct = (now_ - base) / base * 100
            cause = {
                "vessel_delay": f"a vessel delay of {disruption.vessel_delay_hours:g}h",
                "queue_spike": f"a gate queue spike of {disruption.queue_spike_pct:g}%",
            }.get(disruption.kind, "changed conditions")
            reasons.append(
                f"Forecast gate congestion at your original {move.old_slot:%H:%M} slot rose {pct:.0f}% "
                f"because of {cause} (expected wait {base:.0f} -> {now_:.0f} min)."
            )
    if move.new_slot is not None and move.old_slot is not None and move.new_slot != move.old_slot:
        reasons.append(
            f"Moved to {move.new_slot:%H:%M}, where the expected wait is {wait_fn(move.new_slot):.0f} min "
            f"and slot capacity is respected."
        )
    if move.new_slot is None:
        reasons.append("No slot with spare expected capacity was available nearby; booking waitlisted.")
    if risk_summary and move.new_slot != move.old_slot:
        reasons.append(risk_summary)
    return reasons


def slot_board(bookings: list[BookingState], slots: list[datetime], wait_fn: WaitFn, capacity: int = SLOT_CAPACITY):
    rows = []
    for s in slots:
        count, expected = slot_load(bookings, s)
        rows.append(
            {
                "slot": s.isoformat(timespec="minutes"),
                "bookings": count,
                "expected_arrivals": round(expected, 2),
                "capacity": capacity,
                "overbooked": count > capacity,
                "forecast_wait_min": round(wait_fn(s), 1),
            }
        )
    return rows
