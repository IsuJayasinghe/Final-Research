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

import dataclasses
import json
from datetime import datetime, timedelta

import documents
import ml_models
import noshow
import scheduler
import vessels
import weather
from repository import ACTIVE_STATUSES, Appointment
from scheduler import BookingState, Disruption

HIGH_RISK_NOTE_THRESHOLD = 0.15  # mention no-show risk in move explanations above this
MODEL_MAX_MISSING = 3  # the models were trained on 0-3 missing documents
BUSY_QUEUE = 4.0  # a lane with at least this many trucks queued is "busy" ...
CONGESTED_QUEUE = 8.0  # ... and "congested" from this many


LANE_CHANGE_MIN_GAIN = 3.0  # move a truck to another lane only if that lane is at least this many trucks lighter
DELAY_NOTICE_MIN = 5.0  # tell a driver about a delay once the expected wait has grown by this many minutes
EVENT_TITLES = {
    "ASSIGNED": ("Request received", "info"),
    "APPROVED": ("Approved by the gate admin", "success"),
    "REJECTED": ("Request rejected", "error"),
    "REASSIGNED": ("Time slot changed", "warning"),
    "LANE_CHANGED": ("Gate changed", "warning"),
    "DELAY_UPDATE": ("Delay update", "warning"),
    "WAITLISTED": ("Waitlisted", "warning"),
    "DOCUMENTS_CHECKED": ("Documents checked", "info"),
    "CANCELLED": ("Cancelled", "info"),
    "ARRIVED": ("Checked in at the gate", "info"),
    "COMPLETED": ("Gate process complete", "success"),
    "NO_SHOW": ("Marked as no-show", "error"),
}


@dataclasses.dataclass
class LaneClosure:
    """A lane that is out of service for a window (breakdown, maintenance)."""

    lane: int
    start: datetime
    end: datetime
    reason: str = "maintenance"


def lane_status(queue: float) -> str:
    if queue >= CONGESTED_QUEUE:
        return "congested"
    if queue >= BUSY_QUEUE:
        return "busy"
    return "normal"


class BookingError(ValueError):
    """The request cannot be accepted (bad time, unknown id, wrong status)."""


class NotApproved(BookingError):
    """The action needs the gate admin's approval of the appointment first (e.g. uploading documents)."""


def _next_hour(now: datetime) -> datetime:
    return scheduler.hour_floor(now) + timedelta(hours=1)


def _to_state(a: Appointment) -> BookingState:
    return BookingState(a.id, a.requested_slot, a.assigned_slot, a.p_no_show, a.status)


class GateService:
    def __init__(self, repo, require_approval: bool = False):
        self.repo = repo
        # When True (the running app), documents can only be uploaded for an appointment the gate admin has approved.
        self.require_approval = require_approval
        self.disruption: Disruption | None = None
        self.closures: list[LaneClosure] = []
        self._doc_results: dict[int, dict[str, dict]] = {}  # appointment id -> document slot -> OCR verdict

    # -- forecast helpers -------------------------------------------------
    @staticmethod
    def _base_wait(slot: datetime) -> float:
        """Expected wait with no disruption or closure (the normal forecast)."""
        lanes = ml_models.get_all_lane_forecasts(slot)
        return ml_models.estimate_wait_minutes(min(lanes.values()))

    def _is_closed(self, lane: int, slot: datetime) -> bool:
        return any(c.lane == lane and c.start <= slot < c.end for c in self.closures)

    def _closure_reason(self, lane: int, slot: datetime) -> str:
        return next((c.reason for c in self.closures if c.lane == lane and c.start <= slot < c.end), "closed")

    def _queues(self, slot: datetime, include_closed: bool = False) -> dict[int, float]:
        """Forecast queue per lane for a slot: the model forecast, raised by an active disruption (the whole gate or
        one lane). Closed lanes are left out unless `include_closed`."""
        d = self.disruption
        uplift = d.uplift(slot) if d else 0.0
        out = {}
        for lane, queue in ml_models.get_all_lane_forecasts(slot).items():
            if not include_closed and self._is_closed(lane, slot):
                continue
            hit = d is not None and (d.lane is None or d.lane == lane)
            out[lane] = queue * (1 + uplift) if hit else queue
        return out

    def _wait(self, slot: datetime) -> float:
        """Expected wait in a slot now: the best open lane, with any disruption applied."""
        return ml_models.estimate_wait_minutes(min(self._queues(slot).values()))

    def _lane_loads(self, slot: datetime, exclude_id: int | None = None) -> tuple[dict[int, float], dict[int, float]]:
        """(forecast queue, effective load) per OPEN lane. Effective load = forecast queue + trucks already booked on
        that lane in this hour, so a busy hour spreads across the lanes instead of piling onto the quietest one."""
        queues = self._queues(slot)
        booked = {lane: 0 for lane in queues}
        for a in self.repo.list(ACTIVE_STATUSES):
            if a.id != exclude_id and a.assigned_slot == slot and a.lane in booked:
                booked[a.lane] += 1
        return queues, {lane: queues[lane] + booked[lane] for lane in queues}

    def _lane_for(self, slot: datetime, exclude_id: int | None = None) -> tuple[int, float, dict[int, float]]:
        """Lane for a booking in this slot (never a closed lane): the one with the lowest effective load.

        Returns (lane, forecast queue of that lane, forecast queue of every open lane)."""
        queues, loads = self._lane_loads(slot, exclude_id)
        lane = min(loads, key=lambda ln: (loads[ln], ln))
        return lane, queues[lane], queues

    @staticmethod
    def _clearance(a: Appointment, slot: datetime, queue: float) -> float:
        """Predicted clearance minutes. Unknown document facts are averaged over the typical situation."""
        scenarios = noshow.document_scenarios(a.customs_risk_flag, a.missing_documents)
        total = sum(w for _, _, w in scenarios)
        minutes = 0.0
        for customs, missing, weight in scenarios:
            minutes += weight * ml_models.predict_clearance_minutes(
                day_of_week=slot.strftime("%A"),
                container_type=a.container_type,
                cargo_category=a.cargo_category,
                carrier_company=a.carrier,
                arrival_hour=slot.hour,
                queue_length_at_arrival=queue,
                customs_risk_flag=customs,
                carrier_past_reliability_score=a.carrier_reliability,
                missing_documents_count=missing,
            )
        return round(minutes / total, 1)

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

        # Nothing below is typed in by the user. Carrier reliability comes from the carrier's history; weather
        # from the forecast for the arrival day; customs risk and missing documents from OCR of the documents,
        # and the vessel delay from the vessel named on the booking confirmation. Anything not yet known is
        # None and the risk model averages over the typical situation. Callers (tests, simulations) may still
        # pass known values explicitly.
        profile = noshow.carrier_profile(req["carrier"])
        reliability = req.get("carrier_reliability")
        if reliability is None:
            reliability = profile["reliability"] if profile else noshow.DEFAULT_RELIABILITY

        weather_severity = req.get("weather_severity")
        if weather_severity is None:
            weather_info = weather.get_weather(requested.strftime("%Y-%m-%d"))
            weather_severity = weather_info["severity"]
        else:
            weather_info = {
                "date": requested.strftime("%Y-%m-%d"),
                "severity": weather_severity,
                "label": weather.LABELS[weather_severity],
                "source": "entered",
            }
        vessel_delay = req.get("vessel_delay")

        risk = noshow.predict_risk_for_documents(
            req.get("customs_risk_flag"),
            req.get("missing_documents"),
            arrival=requested,
            carrier=req["carrier"],
            container_type=req["container_type"],
            cargo_category=req["cargo_category"],
            carrier_reliability=reliability,
            lead_time_hours=lead_hours,
            weather_severity=weather_severity,
            vessel_delay=vessel_delay,
        )

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
            customs_risk_flag=req.get("customs_risk_flag"),
            missing_documents=req.get("missing_documents"),
            carrier_reliability=reliability,
            p_no_show=risk["p_no_show"],
            p_late=risk["p_late"],
            overbooked=decision.overbooked,
            decision_reason=decision.reason,
            risk_summary=risk["summary"],
            weather_severity=weather_severity,
            weather_source=weather_info["source"],
            vessel_delay=vessel_delay,
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
            "conditions": {
                "weather": weather_info,
                "carrier": {**(profile or {"carrier": req["carrier"]}), "reliability_used": reliability},
                "vessel": {"known": vessel_delay is not None},
            },
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

    # -- OCR document checking -----------------------------------------------
    def check_document(
        self,
        data: bytes,
        filename: str,
        doc_key: str,
        appointment_id: int | None = None,
        ctx: dict | None = None,
    ) -> dict:
        """OCR + validate one upload. With an appointment id, the booking supplies the expected
        container / truck / date and the verdict is remembered for the submission."""
        ctx = dict(ctx or {})
        appointment = None
        if appointment_id is not None:
            appointment = self._require(appointment_id)
            self._require_approved(appointment)
            slot = appointment.assigned_slot or appointment.requested_slot
            ctx.update(
                expected_container_id=appointment.container_id,
                expected_truck_id=appointment.truck_id,
                expected_date=slot.strftime("%Y-%m-%d"),
                expected_time=slot.strftime("%H:%M"),
                container_type=appointment.container_type,
            )
        result = documents.check_document(data, filename, doc_key, ctx)
        if appointment is not None:
            self._doc_results.setdefault(appointment.id, {})[doc_key] = result
        return result

    def document_results(self, appointment_id: int) -> dict:
        self._require(appointment_id)
        return self._doc_results.get(appointment_id, {})

    def _rescore(
        self, a: Appointment, missing: int | None, customs: str | None, vessel_delay: bool | None
    ) -> tuple[dict, float | None]:
        """No-show risk and clearance time for this booking given what is known about its documents and
        linked vessel (None = not known yet, so the typical situation is assumed)."""
        lead = max(1.0, (a.requested_slot - datetime.now()).total_seconds() / 3600)
        risk = noshow.predict_risk_for_documents(
            customs,
            missing,
            arrival=a.requested_slot,
            carrier=a.carrier,
            container_type=a.container_type,
            cargo_category=a.cargo_category,
            carrier_reliability=a.carrier_reliability,
            lead_time_hours=lead,
            weather_severity=a.weather_severity,
            vessel_delay=vessel_delay,
        )
        clearance = None
        if a.assigned_slot:
            _, queue, _ = self._lane_for(a.assigned_slot, exclude_id=a.id)
            clearance = self._clearance(
                dataclasses.replace(a, missing_documents=missing, customs_risk_flag=customs), a.assigned_slot, queue
            )
        return risk, clearance

    def submit_documents(self, appointment_id: int) -> dict:
        """Turn the stored OCR verdicts into a missing-document count and re-score the booking."""
        a = self._require(appointment_id)
        if a.status == "CANCELLED":
            raise BookingError("This appointment is cancelled.")
        self._require_approved(a)
        results = self._doc_results.get(a.id, {})
        if not results:
            raise BookingError("Upload and check at least one document first.")

        required = documents.required_documents(a.container_type)
        statuses = {k: results.get(k, {}).get("status", "missing") for k in required}
        cleared = [k for k, v in statuses.items() if v == "cleared"]
        missing = len(required) - len(cleared)

        # the in-memory repo returns live objects, so read the old values before updating
        old_missing, old_customs = a.missing_documents, a.customs_risk_flag
        cusdec = results.get("cusdec")
        assessment = cusdec.get("customs_assessment") if cusdec else None
        new_customs = assessment["level"] if assessment else old_customs  # unknown stays unknown

        # the linked vessel is named on the booking confirmation; its schedule gives the delay
        old_vessel = a.vessel_delay
        confirmation = results.get("booking_confirmation")
        vessel_name = (confirmation or {}).get("fields", {}).get("vessel_name")
        vessel_info = None
        if vessel_name:
            vessel_info = vessels.get_vessel_delay(vessel_name, (a.assigned_slot or a.requested_slot).strftime("%Y-%m-%d"))
        new_vessel = vessel_info["delayed"] if vessel_info and vessel_info["delayed"] is not None else old_vessel

        before_risk, before_clearance = self._rescore(a, old_missing, old_customs, old_vessel)
        after_risk, after_clearance = self._rescore(a, missing, new_customs, new_vessel)
        summary = f"{len(cleared)} of {len(required)} required documents cleared; {missing} missing or flagged."
        if assessment:
            summary += f" Customs risk from the declaration: {assessment['level']}."
        if vessel_info and vessel_info["delayed"] is not None:
            hours = vessel_info["delay_hours"]
            summary += (
                f" Vessel {vessel_info['vessel']} is delayed {hours:g} h."
                if vessel_info["delayed"]
                else f" Vessel {vessel_info['vessel']} is on schedule."
            )

        vessel_updates = {}
        if vessel_info and vessel_info["delayed"] is not None:
            vessel_updates = {
                "vessel_delay": new_vessel,
                "vessel_name": vessel_info["vessel"],
                "vessel_delay_hours": vessel_info["delay_hours"],
            }
        self.repo.update(
            a.id,
            **vessel_updates,
            missing_documents=missing,
            customs_risk_flag=new_customs,
            p_no_show=after_risk["p_no_show"],
            p_late=after_risk["p_late"],
            risk_summary=after_risk["summary"],
            predicted_clearance_minutes=after_clearance if after_clearance is not None else a.predicted_clearance_minutes,
        )

        def field(name):
            for r in results.values():
                if name in r["fields"]:
                    return r["fields"][name]
            return None

        # how complete each document is against its template, and which details are missing
        completeness = {k: (r.get("template") or {}).get("completeness") for k, r in results.items()}
        missing_details = {k: (r.get("template") or {}).get("missing", []) for k, r in results.items() if (r.get("template") or {}).get("missing")}
        containers = sorted({c for r in results.values() for c in r["fields"].get("container_numbers", [])})
        issues = {k: r["issues"] for k, r in results.items() if r["issues"]}
        self.repo.add_submission(
            a.id,
            cargo_details=json.dumps(
                {
                    "containers": containers,
                    "seal_number": field("seal_number"),
                    "weight_kg": field("weight_kg"),
                    "un_number": field("un_number"),
                    "temperature_c": field("temperature_c"),
                    "booking_no": field("booking_no"),
                }
            ),
            vehicle_details=json.dumps(
                {"truck_id": field("truck_id"), "plate": field("plate"), "licence_no": field("licence_no")}
            ),
            clearance_information=json.dumps(
                {"statuses": statuses, "completeness": completeness, "missing_details": missing_details, "summary": summary, "issues": issues}
            ),
        )
        before_p, after_p = before_risk["p_no_show"], after_risk["p_no_show"]
        reason = f"{summary} No-show risk {before_p:.0%} -> {after_p:.0%}."
        if before_clearance is not None and after_clearance is not None:
            reason += f" Predicted clearance {before_clearance:.0f} -> {after_clearance:.0f} min."
        self.repo.add_event(a.id, "DOCUMENTS_CHECKED", a.assigned_slot, a.assigned_slot, reason)

        return {
            "appointment": self.repo.get(a.id).to_dict(),
            "summary": summary,
            "required": [
                {
                    "doc_key": k,
                    "label": documents.DOCUMENT_LABELS[k],
                    "status": statuses[k],
                    "completeness": (results.get(k, {}).get("template") or {}).get("completeness"),
                    "missing_details": (results.get(k, {}).get("template") or {}).get("missing", []),
                }
                for k in required
            ],
            "cleared": len(cleared),
            "missing": missing,
            "before": {
                "missing_documents": old_missing,
                "customs_risk": old_customs,
                "vessel_delay": old_vessel,
                "p_no_show": before_p,
                "clearance_minutes": before_clearance,
            },
            "after": {
                "missing_documents": missing,
                "customs_risk": new_customs,
                "vessel_delay": new_vessel,
                "p_no_show": after_p,
                "clearance_minutes": after_clearance,
            },
            "customs_assessment": assessment,
            "vessel": vessel_info,
            "drivers": after_risk["drivers"],
            "issues": issues,
            "cross_checks": documents.cross_check(results),
        }

    # -- lifecycle --------------------------------------------------------
    def _require(self, appointment_id: int) -> Appointment:
        a = self.repo.get(appointment_id)
        if a is None:
            raise BookingError(f"Appointment {appointment_id} not found")
        return a

    def _require_approved(self, a: Appointment) -> None:
        """Documents are only accepted after the gate admin approves the appointment."""
        if self.require_approval and a.status != "CONFIRMED":
            wait = {
                "PENDING": "is still waiting for the gate admin to approve it",
                "WAITLISTED": "is on the waiting list",
                "REJECTED": "was rejected by the gate admin",
                "CANCELLED": "is cancelled",
            }.get(a.status, f"is {a.status}")
            raise NotApproved(f"Documents can be uploaded once the gate admin approves the appointment; this one {wait}.")

    def approve(self, appointment_id: int, note: str = "") -> Appointment:
        """Gate admin approves a requested appointment: the slot is fixed and document upload opens."""
        a = self._require(appointment_id)
        if a.status != "PENDING":
            raise BookingError(f"Only appointments awaiting approval can be approved (this one is {a.status}).")
        self.repo.update(appointment_id, status="CONFIRMED")
        message = "Approved by the gate admin. Upload your documents to complete the pre-clearance."
        self.repo.add_event(appointment_id, "APPROVED", a.assigned_slot, a.assigned_slot, (note + " " + message).strip())
        return self.repo.get(appointment_id)

    confirm = approve  # the carrier no longer confirms its own booking; kept for older callers

    def reject(self, appointment_id: int, reason: str = "") -> Appointment:
        """Gate admin declines a requested appointment; the slot is released and the driver sees the reason."""
        a = self._require(appointment_id)
        if a.status not in ("PENDING", "WAITLISTED"):
            raise BookingError(f"Only appointments awaiting approval can be rejected (this one is {a.status}).")
        reason = reason.strip() or "No reason given."
        self.repo.update(appointment_id, status="REJECTED", decision_reason=f"Rejected by the gate admin: {reason}")
        self.repo.add_event(appointment_id, "REJECTED", a.assigned_slot, None, f"Rejected by the gate admin: {reason}")
        return self.repo.get(appointment_id)

    def cancel(self, appointment_id: int) -> Appointment:
        a = self._require(appointment_id)
        if a.status == "CANCELLED":
            raise BookingError("Appointment is already cancelled.")
        if a.status in ("ARRIVED", "COMPLETED", "NO_SHOW"):
            raise BookingError(f"This appointment can no longer be cancelled (it is {a.status}).")
        self.repo.update(appointment_id, status="CANCELLED")
        self.repo.add_event(appointment_id, "CANCELLED", a.assigned_slot, None, "Cancelled by carrier")
        return self.repo.get(appointment_id)

    # -- gate officer: processing a truck at its gate ----------------------------------
    def check_in(self, appointment_id: int, note: str = "") -> Appointment:
        """The truck has reached its gate: the officer starts the gate process."""
        a = self._require(appointment_id)
        if a.status != "CONFIRMED":
            raise BookingError(f"Only approved appointments can be checked in (this one is {a.status}).")
        message = f"Checked in at Gate {a.lane}. Follow the gate officer's instructions."
        self.repo.update(appointment_id, status="ARRIVED")
        self.repo.add_event(appointment_id, "ARRIVED", a.assigned_slot, a.assigned_slot, (note + " " + message).strip())
        return self.repo.get(appointment_id)

    def complete(self, appointment_id: int, note: str = "") -> Appointment:
        """The gate process for this truck is finished (documents, seal and container checked, truck released)."""
        a = self._require(appointment_id)
        if a.status not in ("CONFIRMED", "ARRIVED"):
            raise BookingError(f"Only approved or checked-in appointments can be completed (this one is {a.status}).")
        took = ""
        arrived = [e for e in self.repo.events(appointment_id) if e["event_type"] == "ARRIVED"]
        if arrived:
            minutes = (datetime.now() - datetime.fromisoformat(str(arrived[-1]["event_time"]))).total_seconds() / 60
            took = f" Gate process took {max(minutes, 0):.0f} min."
        self.repo.update(appointment_id, status="COMPLETED")
        message = f"Gate process complete at Gate {a.lane}. You may leave the terminal.{took}"
        self.repo.add_event(appointment_id, "COMPLETED", a.assigned_slot, a.assigned_slot, (note + " " + message).strip())
        return self.repo.get(appointment_id)

    def mark_no_show(self, appointment_id: int, note: str = "") -> Appointment:
        """The truck never came; the officer releases its place."""
        a = self._require(appointment_id)
        if a.status != "CONFIRMED":
            raise BookingError(f"Only approved appointments can be marked as no-show (this one is {a.status}).")
        self.repo.update(appointment_id, status="NO_SHOW")
        self.repo.add_event(appointment_id, "NO_SHOW", a.assigned_slot, None, (note + " Truck did not arrive.").strip())
        return self.repo.get(appointment_id)

    def gate_desk(self, lane: int, date: str | None = None, now: datetime | None = None) -> dict:
        """What one gate officer sees: every booking on this gate for the day, in slot order, with what to do next."""
        now = now or datetime.now()
        if lane not in ml_models.LANE_IDS:
            raise BookingError(f"lane must be one of {ml_models.LANE_IDS}")
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date() if date else now.date()
        except ValueError:
            raise BookingError("date must be YYYY-MM-DD")
        rows = [
            a for a in self.repo.list(("CONFIRMED", "ARRIVED", "COMPLETED", "NO_SHOW"))
            if a.lane == lane and a.assigned_slot is not None and a.assigned_slot.date() == day
        ]
        rows.sort(key=lambda a: (a.assigned_slot, a.id))
        counts = {s: sum(1 for a in rows if a.status == s) for s in ("CONFIRMED", "ARRIVED", "COMPLETED", "NO_SHOW")}
        next_up = next((a.id for a in rows if a.status in ("ARRIVED", "CONFIRMED")), None)
        bookings = []
        for a in rows:
            d = a.to_dict()
            d["docs_state"] = (
                "not uploaded" if a.missing_documents is None else "complete" if a.missing_documents == 0 else f"{a.missing_documents} missing"
            )
            d["minutes_to_slot"] = round((a.assigned_slot - now).total_seconds() / 60)
            d["next_up"] = a.id == next_up
            bookings.append(d)
        closures = [
            {"start": c.start.isoformat(timespec="minutes"), "end": c.end.isoformat(timespec="minutes"), "reason": c.reason}
            for c in self.closures
            if c.lane == lane and c.start.date() <= day <= c.end.date()
        ]
        hour = now.hour if day == now.date() else 8
        queue = None if self._is_closed(lane, datetime.combine(day, datetime.min.time()).replace(hour=hour)) else round(
            self._queues(datetime.combine(day, datetime.min.time()).replace(hour=hour), include_closed=True)[lane], 1
        )
        return {
            "lane": lane,
            "date": day.isoformat(),
            "counts": counts,
            "total": len(rows),
            "closures": closures,
            "queue_now": queue,
            "queue_hour": hour,
            "bookings": bookings,
        }

    def list(self, truck_id: str | None = None, statuses: list[str] | None = None) -> list[dict]:
        rows = self.repo.list(statuses)
        if truck_id:
            wanted = truck_id.strip().upper()
            rows = [a for a in rows if a.truck_id.upper() == wanted]
        return [a.to_dict() for a in rows]

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
        lane: int | None = None,
    ) -> dict:
        now = now or datetime.now()
        earliest = _next_hour(now)
        if lane is not None and lane not in ml_models.LANE_IDS:
            raise BookingError(f"lane must be one of {ml_models.LANE_IDS}")
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
            lane=lane,
        )

        pool = [a for a in self.repo.list(("PENDING", "WAITLISTED"))]
        confirmed = [_to_state(a) for a in self.repo.list(("CONFIRMED", "ARRIVED"))]
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
                lane, queue, _ = self._lane_for(m.new_slot, exclude_id=a.id)
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

        # approved bookings keep their time slot, but their gate (lane) may change; drivers are told about both
        lane_changes = self.rebalance_lanes(now)
        delay_notices = self._notify_delays(now)

        return {
            "disruption": {
                "kind": kind,
                "vessel_delay_hours": vessel_delay_hours,
                "queue_spike_pct": queue_spike_pct,
                "lane": lane,
                "window_start": window_start.isoformat(timespec="minutes"),
                "window_hours": window_hours,
            },
            "considered": len(pool),
            "fixed_confirmed": len(confirmed),
            "moved": len(changes),
            "expected_wait_before_min": round(wait_before, 1),
            "expected_wait_after_min": round(wait_after, 1),
            "changes": changes,
            "lane_changes": lane_changes,
            "delay_notices": delay_notices,
        }

    def clear_disruption(self) -> None:
        self.disruption = None

    # -- gate monitoring ----------------------------------------------------
    @staticmethod
    def _slot(day: str, hour: int) -> datetime:
        try:
            return datetime.strptime(day, "%Y-%m-%d").replace(hour=hour)
        except ValueError:
            raise BookingError("date must be YYYY-MM-DD and hour 0-23")

    def congestion_profile(self, day: str) -> list[dict]:
        """How busy the gate is in each hour of a day (forecast), so the busy hours stand out."""
        booked = {}
        for a in self.repo.list(ACTIVE_STATUSES):
            if a.assigned_slot is not None:
                booked[a.assigned_slot] = booked.get(a.assigned_slot, 0) + 1
        rows = []
        for hour in range(24):
            slot = self._slot(day, hour)
            queues = self._queues(slot)
            worst = max(queues.values())
            rows.append(
                {
                    "hour": hour,
                    "slot": slot.isoformat(timespec="minutes"),
                    "max_lane_queue": round(worst, 1),
                    "total_queue": round(sum(queues.values()), 1),
                    "avg_wait_minutes": ml_models.estimate_wait_minutes(sum(queues.values()) / len(queues)),
                    "status": lane_status(worst),
                    "booked": booked.get(slot, 0),
                    "disrupted": bool(self.disruption and self.disruption.uplift(slot) > 0),
                }
            )
        return rows

    def lane_view(self, day: str, hour: int) -> dict:
        """Every lane at one hour: forecast queue, wait, status, and the real appointments assigned to it.
        Lanes closed in this hour are shown as closed with their reason."""
        slot = self._slot(day, hour)
        queues = self._queues(slot, include_closed=True)
        active = [a for a in self.repo.list(ACTIVE_STATUSES) if a.assigned_slot == slot]
        lanes = []
        for lane in sorted(queues):
            bookings = [a.to_dict() for a in active if a.lane == lane]
            if self._is_closed(lane, slot):
                lanes.append(
                    {
                        "lane": lane,
                        "predicted_queue_length": None,
                        "predicted_avg_wait_minutes": None,
                        "status": "closed",
                        "closed_reason": self._closure_reason(lane, slot),
                        "bookings": bookings,
                    }
                )
                continue
            q = round(queues[lane], 1)
            lanes.append(
                {
                    "lane": lane,
                    "predicted_queue_length": q,
                    "predicted_avg_wait_minutes": ml_models.estimate_wait_minutes(q),
                    "status": lane_status(q),
                    "closed_reason": None,
                    "bookings": bookings,
                }
            )
        disruption = None
        if self.disruption and self.disruption.uplift(slot) > 0:
            disruption = {
                "kind": self.disruption.kind,
                "vessel_delay_hours": self.disruption.vessel_delay_hours,
                "queue_spike_pct": self.disruption.queue_spike_pct,
                "lane": self.disruption.lane,
                "uplift_pct": round(self.disruption.uplift(slot) * 100),
            }
        return {"slot": slot.isoformat(timespec="minutes"), "lanes": lanes, "booked_total": len(active), "disruption": disruption}

    # -- lane closures and automatic gate (lane) changes -----------------------------
    def list_closures(self) -> list[dict]:
        return [
            {"lane": c.lane, "start": c.start.isoformat(timespec="minutes"), "end": c.end.isoformat(timespec="minutes"), "reason": c.reason}
            for c in self.closures
        ]

    def close_lane(self, lane: int, hours: int = 4, start: datetime | str | None = None, reason: str = "", now: datetime | None = None) -> dict:
        """Take a lane out of service for a window (gate admin). Drivers booked on it are moved automatically."""
        now = now or datetime.now()
        if lane not in ml_models.LANE_IDS:
            raise BookingError(f"lane must be one of {ml_models.LANE_IDS}")
        if not 1 <= hours <= 48:
            raise BookingError("hours must be between 1 and 48")
        if isinstance(start, str):
            try:
                start = datetime.fromisoformat(start)
            except ValueError:
                raise BookingError("start must be an ISO datetime, e.g. 2030-01-07T10:00")
        begin = scheduler.hour_floor(start) if start else scheduler.hour_floor(now)
        closure = LaneClosure(lane, begin, begin + timedelta(hours=hours), reason.strip() or "maintenance")
        for h in range(hours):
            slot = begin + timedelta(hours=h)
            still_open = [ln for ln in ml_models.LANE_IDS if ln != lane and not self._is_closed(ln, slot)]
            if not still_open:
                raise BookingError("At least one lane must stay open.")
        self.closures.append(closure)
        return {
            "closure": {"lane": lane, "start": begin.isoformat(timespec="minutes"), "end": closure.end.isoformat(timespec="minutes"), "reason": closure.reason},
            "lane_changes": self.rebalance_lanes(now),
        }

    def reopen_lane(self, lane: int) -> dict:
        before = len(self.closures)
        self.closures = [c for c in self.closures if c.lane != lane]
        return {"reopened": before - len(self.closures)}

    def rebalance_lanes(self, now: datetime | None = None) -> list[dict]:
        """Move drivers to a better lane when theirs closes or becomes much busier than another.

        Approved bookings keep their time slot; only the gate (lane) changes, and the driver gets a notification with
        the reason. Only upcoming hours are touched."""
        now = now or datetime.now()
        floor = scheduler.hour_floor(now)
        upcoming = [
            a for a in self.repo.list(("PENDING", "CONFIRMED"))
            if a.assigned_slot is not None and a.assigned_slot >= floor and a.lane is not None
        ]
        changes = []
        for a in sorted(upcoming, key=lambda x: (x.assigned_slot, x.id)):
            slot = a.assigned_slot
            queues, loads = self._lane_loads(slot, exclude_id=a.id)
            best = min(loads, key=lambda ln: (loads[ln], ln))
            if a.lane not in queues:  # its lane is closed in this hour
                reason = f"Gate {a.lane} is closed ({self._closure_reason(a.lane, slot)}); you were moved to Gate {best}."
            elif best != a.lane and loads[a.lane] - loads[best] >= LANE_CHANGE_MIN_GAIN:
                reason = (
                    f"Gate {a.lane} became {lane_status(queues[a.lane])} (about {queues[a.lane]:.0f} trucks queued); "
                    f"you were moved to Gate {best} ({queues[best]:.0f} trucks)."
                )
            else:
                continue
            old_lane = a.lane  # the in-memory repo returns live objects, so read before updating
            self.repo.update(a.id, lane=best, predicted_clearance_minutes=self._clearance(a, slot, queues[best]))
            self.repo.add_event(a.id, "LANE_CHANGED", slot, slot, reason)
            changes.append(
                {
                    "appointment_id": a.id,
                    "truck_id": a.truck_id,
                    "slot": slot.isoformat(timespec="minutes"),
                    "old_lane": old_lane,
                    "new_lane": best,
                    "reason": reason,
                }
            )
        return changes

    # -- live view for the driver -----------------------------------------------------
    def _delay_cause(self, slot: datetime, lane: int | None) -> str | None:
        d = self.disruption
        if d is None or d.uplift(slot) <= 0 or (d.lane is not None and lane is not None and d.lane != lane):
            return None
        parts = []
        if d.vessel_delay_hours > 0:
            parts.append(f"a vessel delay of {d.vessel_delay_hours:g} h")
        if d.queue_spike_pct > 0:
            parts.append(f"a queue spike of +{d.queue_spike_pct:g}%" + (f" at Gate {d.lane}" if d.lane is not None else ""))
        return " and ".join(parts) or "changed conditions"

    def _live_wait(self, a: Appointment) -> tuple[float, float]:
        """(normal expected wait, expected wait now) at this booking's lane."""
        slot = a.assigned_slot
        base_q = ml_models.get_all_lane_forecasts(slot)[a.lane]
        live_q = self._queues(slot, include_closed=True)[a.lane]
        return ml_models.estimate_wait_minutes(base_q), ml_models.estimate_wait_minutes(live_q)

    def _notify_delays(self, now: datetime | None = None) -> int:
        """Tell drivers whose expected wait has grown because of a disruption (once per distinct update)."""
        now = now or datetime.now()
        floor = scheduler.hour_floor(now)
        sent = 0
        for a in self.repo.list(("PENDING", "CONFIRMED")):
            if a.assigned_slot is None or a.lane is None or a.assigned_slot < floor or self._is_closed(a.lane, a.assigned_slot):
                continue
            cause = self._delay_cause(a.assigned_slot, a.lane)
            if cause is None:
                continue
            base, live = self._live_wait(a)
            if live - base < DELAY_NOTICE_MIN:
                continue
            message = f"Expected wait at Gate {a.lane} for your {a.assigned_slot:%H:%M} slot rose from {base:.0f} to {live:.0f} min because of {cause}."
            events = self.repo.events(a.id)
            if any(e["event_type"] == "DELAY_UPDATE" and e["reason"] == message for e in events[-3:]):
                continue
            self.repo.add_event(a.id, "DELAY_UPDATE", a.assigned_slot, a.assigned_slot, message)
            sent += 1
        return sent

    def notifications(self, appointment_id: int, limit: int = 30) -> list[dict]:
        """What the driver should be told, newest first (approval, gate or slot changes, delays ...)."""
        self._require(appointment_id)
        out = []
        for e in reversed(self.repo.events(appointment_id)):
            title, level = EVENT_TITLES.get(e["event_type"], (e["event_type"].replace("_", " ").title(), "info"))
            out.append({"time": e["event_time"], "type": e["event_type"], "title": title, "level": level, "message": e["reason"]})
        return out[:limit]

    def live(self, appointment_id: int, now: datetime | None = None) -> dict:
        """The driver's live view of one appointment: where it stands, which gate and slot, and what the gate looks like
        for that hour right now, including how much the expected wait has moved and why."""
        now = now or datetime.now()
        a = self._require(appointment_id)
        slot = a.assigned_slot
        base = {"appointment": a.to_dict(), "notifications": self.notifications(appointment_id, 10)}

        steps = {
            "PENDING": ("awaiting_approval", "Waiting for the gate admin to approve your request."),
            "WAITLISTED": ("waitlisted", "No slot was free. You are on the waiting list."),
            "REJECTED": ("rejected", "The gate admin rejected this request. See the reason and book another time."),
            "CANCELLED": ("cancelled", "This appointment was cancelled."),
            "ARRIVED": ("at_gate", f"You are checked in at Gate {a.lane}. The gate officer is processing your truck."),
            "COMPLETED": ("completed", "Gate process complete. You may leave the terminal."),
            "NO_SHOW": ("no_show", "You did not arrive for this slot, so the gate officer released it. Book a new time."),
        }
        if a.status in steps or slot is None or a.lane is None:
            phase, step = steps.get(a.status, ("waiting", "Waiting for a slot."))
            return {**base, "phase": phase, "next_step": step, "live": None}

        base_wait, live_wait = self._live_wait(a)
        closed = self._is_closed(a.lane, slot)
        queue = None if closed else round(self._queues(slot, include_closed=True)[a.lane], 1)
        delay = round(live_wait - base_wait, 1)
        reasons = []
        cause = self._delay_cause(slot, a.lane)
        if cause and delay >= 1:
            reasons.append(f"Congestion at your gate is up because of {cause}.")
        if a.vessel_delay:
            hours = f" {a.vessel_delay_hours:g} h" if a.vessel_delay_hours else ""
            reasons.append(f"Your linked vessel{' ' + a.vessel_name if a.vessel_name else ''} is delayed{hours}.")
        if closed:
            reasons.append(f"Gate {a.lane} is closed ({self._closure_reason(a.lane, slot)}); a gate change is pending.")
        entry = slot + timedelta(minutes=live_wait)
        departure = entry + timedelta(minutes=a.predicted_clearance_minutes or 0)

        minutes_to_slot = round((slot - now).total_seconds() / 60)
        if minutes_to_slot > 0:
            if a.missing_documents is None:
                phase, step = "upload_documents", "Approved. Upload your documents before your slot."
            elif a.missing_documents:
                phase, step = "fix_documents", f"{a.missing_documents} document(s) are missing or flagged. Fix them before your slot."
            else:
                phase, step = "ready", f"All set. Arrive at Gate {a.lane} at {slot:%H:%M}."
        elif minutes_to_slot > -60:
            phase, step = "arrive_now", f"Your slot is now. Go to Gate {a.lane}."
        else:
            phase, step = "past", "Your slot has passed."

        return {
            **base,
            "phase": phase,
            "next_step": step,
            "minutes_to_slot": minutes_to_slot,
            "live": {
                "slot": slot.isoformat(timespec="minutes"),
                "lane": a.lane,
                "lane_status": "closed" if closed else lane_status(queue),
                "queue": queue,
                "normal_wait_min": round(base_wait, 1),
                "expected_wait_min": round(live_wait, 1),
                "delay_min": delay,
                "gate_entry": entry.isoformat(timespec="minutes"),
                "departure": departure.isoformat(timespec="minutes"),
                "reasons": reasons,
                "monitor": {"date": slot.strftime("%Y-%m-%d"), "hour": slot.hour},
            },
        }

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
    _service = GateService(repo, require_approval=True)  # the running app: documents unlock after admin approval
    return _service


def get_service() -> GateService:
    if _service is None:
        raise RuntimeError("Gate service not initialised")
    return _service
