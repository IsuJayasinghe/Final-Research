"""
Appointment storage for Component 4.

Two interchangeable repositories:
  PostgresRepository - writes to the shared PostgreSQL `gate.*` tables
                       (needs database/migrations/001_gate_appointment_predictions.sql)
  MemoryRepository   - in-process store, used when no DATABASE_URL is configured
                       so the API and demo still run on a machine without the DB

Pick one with get_repository(); credentials come from the DATABASE_URL environment
variable (see .env.example) and are never committed.
"""

from __future__ import annotations

import itertools
import os
import threading
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Iterable

ACTIVE_STATUSES = ("PENDING", "CONFIRMED")


@dataclass
class Appointment:
    truck_id: str
    container_id: str
    carrier: str
    container_type: str
    cargo_category: str
    requested_slot: datetime
    assigned_slot: datetime | None = None
    lane: int | None = None
    status: str = "PENDING"  # PENDING (unconfirmed) | CONFIRMED | WAITLISTED | CANCELLED
    customs_risk_flag: str = "low"
    missing_documents: int = 0
    carrier_reliability: float = 0.75
    p_no_show: float = 0.0
    p_late: float = 0.0
    predicted_clearance_minutes: float | None = None
    overbooked: bool = False
    decision_reason: str = ""
    risk_summary: str = ""
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("requested_slot", "assigned_slot", "created_at"):
            d[k] = d[k].isoformat(timespec="minutes") if d[k] else None
        return d


_UPDATABLE = {f.name for f in fields(Appointment)} - {"id", "created_at"}


class MemoryRepository:
    kind = "memory"

    def __init__(self):
        self._rows: dict[int, Appointment] = {}
        self._events: list[dict] = []
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def add(self, a: Appointment) -> Appointment:
        with self._lock:
            a.id = next(self._ids)
            self._rows[a.id] = a
        return a

    def get(self, appointment_id: int) -> Appointment | None:
        return self._rows.get(appointment_id)

    def list(self, statuses: Iterable[str] | None = None) -> list[Appointment]:
        rows = sorted(self._rows.values(), key=lambda a: a.id)
        return [a for a in rows if statuses is None or a.status in statuses]

    def update(self, appointment_id: int, **changes) -> Appointment:
        bad = set(changes) - _UPDATABLE
        if bad:
            raise ValueError(f"Cannot update fields: {sorted(bad)}")
        a = self._rows[appointment_id]
        for k, v in changes.items():
            setattr(a, k, v)
        return a

    def add_event(self, appointment_id, event_type, old_slot=None, new_slot=None, reason=""):
        self._events.append(
            {
                "appointment_id": appointment_id,
                "event_time": datetime.now().isoformat(timespec="seconds"),
                "event_type": event_type,
                "old_arrival": old_slot.isoformat(timespec="minutes") if old_slot else None,
                "new_arrival": new_slot.isoformat(timespec="minutes") if new_slot else None,
                "reason": reason,
            }
        )

    def events(self, appointment_id: int) -> list[dict]:
        return [e for e in self._events if e["appointment_id"] == appointment_id]

    def clear(self):
        self._rows.clear()
        self._events.clear()


class PostgresRepository:
    kind = "postgresql"

    _COLUMNS = (
        "appointment_id, external_truck_id, container_id, carrier_company, container_type, cargo_category, "
        "requested_arrival, assigned_arrival, gate_id, appointment_status, customs_risk_flag, "
        "missing_documents_count, carrier_reliability_score, no_show_probability, late_probability, "
        "predicted_clearance_minutes, overbooked, decision_reason, risk_summary, created_at"
    )

    def __init__(self, url: str):
        import psycopg  # imported lazily so the memory fallback needs no driver

        self._psycopg = psycopg
        self._url = url
        with self._connect() as conn:  # fail fast if the DB or migration is missing
            conn.execute("SELECT 1 FROM gate.gate_appointment_events LIMIT 0")

    def _connect(self):
        from psycopg.rows import dict_row

        return self._psycopg.connect(self._url, row_factory=dict_row)

    @staticmethod
    def _lane(gate_id):
        return int(gate_id.split("-")[1]) if gate_id else None

    def _to_obj(self, r: dict) -> Appointment:
        return Appointment(
            id=r["appointment_id"],
            truck_id=r["external_truck_id"],
            container_id=r["container_id"],
            carrier=r["carrier_company"],
            container_type=r["container_type"],
            cargo_category=r["cargo_category"],
            requested_slot=r["requested_arrival"],
            assigned_slot=r["assigned_arrival"],
            lane=self._lane(r["gate_id"]),
            status=r["appointment_status"],
            customs_risk_flag=r["customs_risk_flag"] or "low",
            missing_documents=r["missing_documents_count"] or 0,
            carrier_reliability=float(r["carrier_reliability_score"] or 0),
            p_no_show=float(r["no_show_probability"] or 0),
            p_late=float(r["late_probability"] or 0),
            predicted_clearance_minutes=(
                float(r["predicted_clearance_minutes"]) if r["predicted_clearance_minutes"] is not None else None
            ),
            overbooked=bool(r["overbooked"]),
            decision_reason=r["decision_reason"] or "",
            risk_summary=r["risk_summary"] or "",
            created_at=r["created_at"],
        )

    def add(self, a: Appointment) -> Appointment:
        with self._connect() as conn:
            # common.containers is the shared registry gate_appointments references
            conn.execute(
                "INSERT INTO common.containers (container_id, container_type, cargo_type) "
                "VALUES (%s, %s, %s) ON CONFLICT (container_id) DO NOTHING",
                (a.container_id, a.container_type, a.cargo_category),
            )
            row = conn.execute(
                "INSERT INTO gate.gate_appointments (external_truck_id, container_id, carrier_company, "
                "container_type, cargo_category, requested_arrival, assigned_arrival, gate_id, "
                "appointment_status, customs_risk_flag, missing_documents_count, carrier_reliability_score, "
                "no_show_probability, late_probability, predicted_clearance_minutes, overbooked, "
                "decision_reason, risk_summary, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING appointment_id",
                (
                    a.truck_id, a.container_id, a.carrier, a.container_type, a.cargo_category,
                    a.requested_slot, a.assigned_slot, f"GATE-{a.lane}" if a.lane else None, a.status,
                    a.customs_risk_flag, a.missing_documents, a.carrier_reliability, a.p_no_show, a.p_late,
                    a.predicted_clearance_minutes, a.overbooked, a.decision_reason, a.risk_summary, a.created_at,
                ),
            ).fetchone()
        a.id = row["appointment_id"]
        return a

    def get(self, appointment_id: int) -> Appointment | None:
        with self._connect() as conn:
            r = conn.execute(
                f"SELECT {self._COLUMNS} FROM gate.gate_appointments WHERE appointment_id = %s", (appointment_id,)
            ).fetchone()
        return self._to_obj(r) if r else None

    def list(self, statuses: Iterable[str] | None = None) -> list[Appointment]:
        sql = f"SELECT {self._COLUMNS} FROM gate.gate_appointments"
        params: tuple = ()
        if statuses is not None:
            sql += " WHERE appointment_status = ANY(%s)"
            params = (list(statuses),)
        with self._connect() as conn:
            rows = conn.execute(sql + " ORDER BY appointment_id", params).fetchall()
        return [self._to_obj(r) for r in rows]

    _COLUMN_FOR = {
        "assigned_slot": "assigned_arrival",
        "requested_slot": "requested_arrival",
        "status": "appointment_status",
        "p_no_show": "no_show_probability",
        "p_late": "late_probability",
        "missing_documents": "missing_documents_count",
        "carrier_reliability": "carrier_reliability_score",
        "carrier": "carrier_company",
        "truck_id": "external_truck_id",
    }

    def update(self, appointment_id: int, **changes) -> Appointment:
        bad = set(changes) - _UPDATABLE
        if bad:
            raise ValueError(f"Cannot update fields: {sorted(bad)}")
        sets, params = [], []
        for key, value in changes.items():
            if key == "lane":
                sets.append("gate_id = %s")
                params.append(f"GATE-{value}" if value else None)
            else:
                sets.append(f"{self._COLUMN_FOR.get(key, key)} = %s")
                params.append(value)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE gate.gate_appointments SET {', '.join(sets)} WHERE appointment_id = %s",
                (*params, appointment_id),
            )
        return self.get(appointment_id)

    def add_event(self, appointment_id, event_type, old_slot=None, new_slot=None, reason=""):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO gate.gate_appointment_events (appointment_id, event_type, old_arrival, new_arrival, reason) "
                "VALUES (%s, %s, %s, %s, %s)",
                (appointment_id, event_type, old_slot, new_slot, reason),
            )

    def events(self, appointment_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_time, event_type, old_arrival, new_arrival, reason "
                "FROM gate.gate_appointment_events WHERE appointment_id = %s ORDER BY event_id",
                (appointment_id,),
            ).fetchall()
        return [
            {
                "appointment_id": appointment_id,
                "event_time": r["event_time"].isoformat(timespec="seconds"),
                "event_type": r["event_type"],
                "old_arrival": r["old_arrival"].isoformat(timespec="minutes") if r["old_arrival"] else None,
                "new_arrival": r["new_arrival"].isoformat(timespec="minutes") if r["new_arrival"] else None,
                "reason": r["reason"] or "",
            }
            for r in rows
        ]


def get_repository():
    """PostgreSQL when DATABASE_URL is set, otherwise an in-memory store."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    url = os.environ.get("DATABASE_URL")
    if not url:
        return MemoryRepository()
    return PostgresRepository(url)
