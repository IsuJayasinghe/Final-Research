"""Repository contract tests: the same behaviour must hold for memory and PostgreSQL.

The PostgreSQL case runs only when TEST_DATABASE_URL points at a database that has
the team schema plus database/migrations/001_gate_appointment_predictions.sql.
"""

import os
from datetime import datetime

import pytest

from repository import Appointment, MemoryRepository, PostgresRepository

SLOT = datetime(2030, 1, 7, 9, 0)


def make(**kw):
    base = dict(
        truck_id="TRK-1",
        container_id="MAEU1234567",
        carrier="Carrier-A",
        container_type="hazardous",
        cargo_category="export",
        requested_slot=SLOT,
        assigned_slot=SLOT,
        lane=3,
        customs_risk_flag="high",
        missing_documents=2,
        carrier_reliability=0.61,
        p_no_show=0.2345,
        p_late=0.31,
        predicted_clearance_minutes=48.5,
        overbooked=True,
        decision_reason="Overbooked requested slot",
        risk_summary="No-show risk 23%.",
        weather_severity=2,
        vessel_delay=True,
    )
    base.update(kw)
    return Appointment(**base)


@pytest.fixture(params=["memory", "postgres"])
def repo(request):
    if request.param == "memory":
        yield MemoryRepository()
        return
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    r = PostgresRepository(url)
    with r._connect() as conn:
        conn.execute("TRUNCATE gate.gate_appointment_events, gate.gate_appointments RESTART IDENTITY CASCADE")
    yield r


def test_add_and_get_round_trip(repo):
    saved = repo.add(make())
    assert saved.id is not None
    got = repo.get(saved.id)
    assert got.truck_id == "TRK-1" and got.lane == 3 and got.status == "PENDING"
    assert got.assigned_slot == SLOT and got.requested_slot == SLOT
    assert got.p_no_show == pytest.approx(0.2345, abs=1e-4)
    assert got.predicted_clearance_minutes == pytest.approx(48.5)
    assert got.overbooked is True and got.risk_summary == "No-show risk 23%."
    assert got.weather_severity == 2 and got.vessel_delay is True


def test_waitlisted_booking_has_no_slot_or_lane(repo):
    saved = repo.add(make(assigned_slot=None, lane=None, status="WAITLISTED"))
    got = repo.get(saved.id)
    assert got.assigned_slot is None and got.lane is None and got.status == "WAITLISTED"


def test_list_filters_by_status(repo):
    a = repo.add(make(truck_id="A"))
    b = repo.add(make(truck_id="B", container_id="MAEU7654321"))
    repo.update(b.id, status="CONFIRMED")
    assert [x.id for x in repo.list()] == [a.id, b.id]
    assert [x.id for x in repo.list(statuses=["CONFIRMED"])] == [b.id]


def test_update_moves_slot_and_lane(repo):
    a = repo.add(make())
    new_slot = datetime(2030, 1, 7, 11, 0)
    updated = repo.update(a.id, assigned_slot=new_slot, lane=5, decision_reason="moved")
    assert updated.assigned_slot == new_slot and updated.lane == 5 and updated.decision_reason == "moved"


def test_update_rejects_unknown_fields(repo):
    a = repo.add(make())
    with pytest.raises(ValueError):
        repo.update(a.id, nonsense=1)


def test_events_are_kept_in_order(repo):
    a = repo.add(make())
    repo.add_event(a.id, "ASSIGNED", None, SLOT, "first")
    repo.add_event(a.id, "REASSIGNED", SLOT, datetime(2030, 1, 7, 10, 0), "vessel delay")
    ev = repo.events(a.id)
    assert [e["event_type"] for e in ev] == ["ASSIGNED", "REASSIGNED"]
    assert ev[1]["reason"] == "vessel delay" and ev[1]["new_arrival"].startswith("2030-01-07T10:00")


def test_get_missing_returns_none(repo):
    assert repo.get(999999) is None


def test_document_submissions_are_stored_per_appointment(repo):
    a = repo.add(make())
    b = repo.add(make(truck_id="B", container_id="MAEU7654321"))
    repo.add_submission(a.id, '{"seal": "SL1"}', '{"plate": "WP CAB-1234"}', '{"missing": 0}')
    repo.add_submission(b.id, "{}", "{}", '{"missing": 2}')
    got = repo.submissions(a.id)
    assert len(got) == 1 and got[0]["cargo_details"] == '{"seal": "SL1"}' and got[0]["clearance_information"] == '{"missing": 0}'
    assert repo.submissions(b.id)[0]["clearance_information"] == '{"missing": 2}'


def test_unchecked_documents_stay_unknown_not_zero(repo):
    saved = repo.add(make(customs_risk_flag=None, missing_documents=None))
    got = repo.get(saved.id)
    assert got.customs_risk_flag is None and got.missing_documents is None
    repo.update(saved.id, customs_risk_flag="medium", missing_documents=1)
    got = repo.get(saved.id)
    assert got.customs_risk_flag == "medium" and got.missing_documents == 1


def test_conditions_can_be_unknown_and_vessel_details_round_trip(repo):
    saved = repo.add(make(weather_severity=None, vessel_delay=None))
    got = repo.get(saved.id)
    assert got.weather_severity is None and got.vessel_delay is None and got.vessel_name is None
    repo.update(saved.id, weather_severity=2, weather_source="open-meteo", vessel_delay=True,
                vessel_name="MV OCEAN PIONEER", vessel_delay_hours=5.0)
    got = repo.get(saved.id)
    assert got.weather_severity == 2 and got.weather_source == "open-meteo" and got.vessel_delay is True
    assert got.vessel_name == "MV OCEAN PIONEER" and got.vessel_delay_hours == 5.0
    # False is a real answer ("on time"), different from unknown
    repo.update(saved.id, vessel_delay=False)
    assert repo.get(saved.id).vessel_delay is False
