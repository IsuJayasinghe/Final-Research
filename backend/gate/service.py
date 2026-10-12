"""
Gate appointment service: orchestrates the two models, the overbooking decision
layer and storage.

    booking -> Model 2 (no-show risk + SHAP) -> overbooking rule picks the slot
            -> Model 1 (congestion forecast) picks the lane and expected wait
            -> clearance model predicts time at the gate -> saved with its reasons

    disruption (vessel delay / queue spike) -> re-optimize UNCONFIRMED bookings,
            every move saved with a plain-language explanation
"""

from __future__ import annotations

from datetime import datetime, timedelta

import ml_models
import noshow
import scheduler
from repository import ACTIVE_STATUSES, Appointment
from scheduler import BookingState, Disruption

HIGH_RISK_NOTE_THRESHOLD = 0.15  # mention no-show risk in move explanations above this


class BookingError(ValueError):
    """The request cannot be accepted (bad time, unknown id, wrong status)."""


def _next_hour(now: datetime) -> datetime:
    return scheduler.hour_floor(now) + timedelta(hours=1)


def _to_state(a: Appointment) -> BookingState:
    return BookingState(a.id, a.requested_slot, a.assigned_slot, a.p_no_show, a.status)


class GateService:
    def __init__(self, repo):
        self.repo = repo
        self.disruption: Disruption | None = None

    # -- forecast helpers -------------------------------------------------
    @staticmethod
    def _base_wait(slot: datetime) -> float:
        lanes = ml_models.get_all_lane_forecasts(slot)
        return ml_models.estimate_wait_minutes(min(lanes.values()))

    def _wait(self, slot: datetime) -> float:
        base = self._base_wait(slot)
        if self.disruption is None:
            return base
        return base * (1 + self.disruption.uplift(slot))

    @staticmethod
    def _lane_for(slot: datetime) -> tuple[int, float, dict[int, float]]:
        forecasts = ml_models.get_all_lane_forecasts(slot)
        lane = min(forecasts, key=forecasts.get)
        return lane, forecasts[lane], forecasts

    @staticmethod
    def _clearance(a: Appointment, slot: datetime, queue: float) -> float:
        return ml_models.predict_clearance_minutes(
            day_of_week=slot.strftime("%A"),
            container_type=a.container_type,
            cargo_category=a.cargo_category,
            carrier_company=a.carrier,
            arrival_hour=slot.hour,
            queue_length_at_arrival=queue,
            customs_risk_flag=a.customs_risk_flag,
            carrier_past_reliability_score=a.carrier_reliability,
            missing_documents_count=a.missing_documents,
        )

    # -- booking ----------------------------------------------------------
    def create(self, req: dict, now: datetime | None = None) -> dict:
        now = now or datetime.now()
        if not req.get("arrival_date") or req.get("arrival_hour") is None:
            raise BookingError("arrival_date and arrival_hour are required")
        try:
            requested = datetime.strptime(req["arrival_date"], "%Y-%m-%d").replace(hour=req["arrival_hour"])
        except ValueError:
            raise BookingError("arrival_date must be YYYY-MM-DD")
        earliest = _next_hour(now)
        if requested < earliest:
            raise BookingError("Planned arrival must be in the future (next full hour or later).")

        lead_hours = (requested - now).total_seconds() / 3600
        row = noshow.build_row(
            arrival=requested,
            carrier=req["carrier"],
            container_type=req["container_type"],
            cargo_category=req["cargo_category"],
            customs_risk_flag=req["customs_risk_flag"],
            missing_documents=req["missing_documents"],
            carrier_reliability=req["carrier_reliability"],
            lead_time_hours=lead_hours,
            weather_severity=req.get("weather_severity", 0),
            vessel_delay=req.get("vessel_delay", False),
        )
        risk = noshow.predict_risk(row)

        states = [_to_state(a) for a in self.repo.list(ACTIVE_STATUSES)]
        decision = scheduler.decide_slot(requested, risk["p_no_show"], states, earliest, self._wait)

        a = Appointment(
            truck_id=req["truck_id"],
            container_id=req["container_id"],
            carrier=req["carrier"],
            container_type=req["container_type"],
            cargo_category=req["cargo_category"],
            requested_slot=requested,
            assigned_slot=decision.slot,
            status=decision.status,
            customs_risk_flag=req["customs_risk_flag"],
            missing_documents=req["missing_documents"],
            carrier_reliability=req["carrier_reliability"],
            p_no_show=risk["p_no_show"],
            p_late=risk["p_late"],
            overbooked=decision.overbooked,
            decision_reason=decision.reason,
            risk_summary=risk["summary"],
        )
        lanes = []
        wait = gate_entry = departure = None
        if decision.slot:
            a.lane, queue, forecasts = self._lane_for(decision.slot)
            a.predicted_clearance_minutes = self._clearance(a, decision.slot, queue)
            wait = self._wait(decision.slot)
            gate_entry = decision.slot + timedelta(minutes=wait)
            departure = gate_entry + timedelta(minutes=a.predicted_clearance_minutes)
            lanes = [
                {
                    "lane": ln,
                    "predicted_queue_length": q,
                    "predicted_avg_wait_minutes": ml_models.estimate_wait_minutes(q),
                }
                for ln, q in sorted(forecasts.items())
            ]
        a = self.repo.add(a)
        self.repo.add_event(a.id, "ASSIGNED" if decision.slot else "WAITLISTED", None, decision.slot, decision.reason)

        return {
            "appointment": a.to_dict(),
            "risk": risk,
            "decision": {
                "overbooked": decision.overbooked,
                "reason": decision.reason,
                "expected_arrivals_before": decision.expected_before,
                "expected_arrivals_after": decision.expected_after,
                "bookings_in_slot": decision.bookings_after,
                "capacity": scheduler.SLOT_CAPACITY,
                "candidates": decision.candidates,
            },
            "timing": {
                "predicted_wait_minutes": round(wait, 1) if wait is not None else None,
                "gate_entry": gate_entry.isoformat(timespec="minutes") if gate_entry else None,
                "departure": departure.isoformat(timespec="minutes") if departure else None,
            },
            "lanes": lanes,
        }

    # -- lifecycle --------------------------------------------------------
    def _require(self, appointment_id: int) -> Appointment:
        a = self.repo.get(appointment_id)
        if a is None:
            raise BookingError(f"Appointment {appointment_id} not found")
        return a

    def confirm(self, appointment_id: int) -> Appointment:
        a = self._require(appointment_id)
        if a.status != "PENDING":
            raise BookingError(f"Only PENDING appointments can be confirmed (this one is {a.status}).")
        self.repo.update(appointment_id, status="CONFIRMED")
        self.repo.add_event(appointment_id, "CONFIRMED", a.assigned_slot, a.assigned_slot, "Confirmed by carrier")
        return self.repo.get(appointment_id)

    def cancel(self, appointment_id: int) -> Appointment:
        a = self._require(appointment_id)
        if a.status == "CANCELLED":
            raise BookingError("Appointment is already cancelled.")
        self.repo.update(appointment_id, status="CANCELLED")
        self.repo.add_event(appointment_id, "CANCELLED", a.assigned_slot, None, "Cancelled by carrier")
        return self.repo.get(appointment_id)

    def list(self) -> list[dict]:
        return [a.to_dict() for a in self.repo.list()]

    def events(self, appointment_id: int) -> list[dict]:
        self._require(appointment_id)
        return self.repo.events(appointment_id)

    # -- disruption and re-optimization ----------------------------------
    def reoptimize(
        self,
        vessel_delay_hours: float = 0.0,
        queue_spike_pct: float = 0.0,
        window_hours: int = 4,
        start: datetime | str | None = None,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now()
        earliest = _next_hour(now)
        if isinstance(start, str):
            try:
                start = datetime.fromisoformat(start)
            except ValueError:
                raise BookingError("start must be an ISO datetime, e.g. 2030-01-07T10:00")
        window_start = scheduler.hour_floor(start) if start else earliest
        if vessel_delay_hours > 0 and queue_spike_pct > 0:
            kind = "vessel_delay"  # describe by the dominant cause; both raise congestion
        else:
            kind = "vessel_delay" if vessel_delay_hours > 0 else "queue_spike" if queue_spike_pct > 0 else "none"
        self.disruption = Disruption(
            kind=kind,
            vessel_delay_hours=vessel_delay_hours,
            queue_spike_pct=queue_spike_pct,
            start=window_start,
            window_hours=window_hours,
        )

        pool = [a for a in self.repo.list(("PENDING", "WAITLISTED"))]
        confirmed = [_to_state(a) for a in self.repo.list(("CONFIRMED",))]
        by_id = {a.id: a for a in pool}
        moves = scheduler.reoptimize([_to_state(a) for a in pool], confirmed, earliest, self._wait)

        changes = []
        wait_before = wait_after = 0.0
        for m in moves:
            a = by_id[m.booking_id]
            wait_before += self._wait(m.old_slot) if m.old_slot else 0.0
            wait_after += self._wait(m.new_slot) if m.new_slot else 0.0
            if m.new_slot == m.old_slot:
                continue
            risk_note = a.risk_summary if a.p_no_show >= HIGH_RISK_NOTE_THRESHOLD else None
            reasons = scheduler.explain_move(m, self._base_wait, self._wait, self.disruption, risk_note)
            if m.new_slot is None:
                self.repo.update(a.id, assigned_slot=None, lane=None, status="WAITLISTED", decision_reason=" ".join(reasons))
                self.repo.add_event(a.id, "WAITLISTED", m.old_slot, None, " ".join(reasons))
            else:
                lane, queue, _ = self._lane_for(m.new_slot)
                clearance = self._clearance(a, m.new_slot, queue)
                self.repo.update(
                    a.id,
                    assigned_slot=m.new_slot,
                    lane=lane,
                    status="PENDING",
                    predicted_clearance_minutes=clearance,
                    decision_reason=" ".join(reasons),
                )
                self.repo.add_event(a.id, "REASSIGNED", m.old_slot, m.new_slot, " ".join(reasons))
            changes.append(
                {
                    "appointment_id": a.id,
                    "truck_id": a.truck_id,
                    "old_slot": m.old_slot.isoformat(timespec="minutes") if m.old_slot else None,
                    "new_slot": m.new_slot.isoformat(timespec="minutes") if m.new_slot else None,
                    "reasons": reasons,
                }
            )

        return {
            "disruption": {
                "kind": kind,
                "vessel_delay_hours": vessel_delay_hours,
                "queue_spike_pct": queue_spike_pct,
                "window_start": window_start.isoformat(timespec="minutes"),
                "window_hours": window_hours,
            },
            "considered": len(pool),
            "fixed_confirmed": len(confirmed),
            "moved": len(changes),
            "expected_wait_before_min": round(wait_before, 1),
            "expected_wait_after_min": round(wait_after, 1),
            "changes": changes,
        }

    def clear_disruption(self) -> None:
        self.disruption = None

    # -- slot board -------------------------------------------------------
    def slot_board(self, date: str) -> list[dict]:
        try:
            day = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise BookingError("date must be YYYY-MM-DD")
        slots = [day + timedelta(hours=h) for h in range(24)]
        states = [_to_state(a) for a in self.repo.list(ACTIVE_STATUSES)]
        return scheduler.slot_board(states, slots, self._wait)


_service: GateService | None = None


def init(repo) -> GateService:
    global _service
    _service = GateService(repo)
    return _service


def get_service() -> GateService:
    if _service is None:
        raise RuntimeError("Gate service not initialised")
    return _service
