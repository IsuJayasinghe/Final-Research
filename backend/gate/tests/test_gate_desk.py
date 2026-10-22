"""The gate officer's desk: pick one gate, see its trucks, check them in and complete the gate process."""

from datetime import datetime

import pytest

import ml_models
import noshow
from fastapi.testclient import TestClient
from repository import MemoryRepository
from service import BookingError, GateService

DATE = "2030-01-07"
NOW = datetime(2030, 1, 7, 6, 30)


@pytest.fixture(scope="module", autouse=True)
def _models():
    ml_models.load_models()
    noshow.load_model()


@pytest.fixture
def svc():
    return GateService(MemoryRepository(), require_approval=True)


def book(svc, i, hour=10, approve=True):
    a = svc.create(
        dict(truck_id=f"TRK-{i}", container_id="CSQU3054383", carrier="Carrier-A", cargo_category="export",
             container_type="standard", arrival_date=DATE, arrival_hour=hour, weather_severity=0, vessel_delay=False),
        now=NOW,
    )["appointment"]
    if approve:
        svc.approve(a["id"])
    return a["id"]


def test_the_desk_shows_only_that_gates_approved_trucks_in_slot_order(svc):
    ids = [book(svc, i, hour=h) for i, h in [(1, 11), (2, 9), (3, 10)]]
    pending = book(svc, 4, approve=False)
    lane = svc.repo.get(ids[0]).lane
    desk = svc.gate_desk(lane, DATE, now=NOW)
    shown = [b["id"] for b in desk["bookings"]]
    assert pending not in shown  # not approved yet: not the officer's job
    assert all(svc.repo.get(i).lane == lane for i in shown)
    slots = [b["assigned_slot"] for b in desk["bookings"]]
    assert slots == sorted(slots)
    assert desk["bookings"][0]["next_up"] and not any(b["next_up"] for b in desk["bookings"][1:])


def test_check_in_then_complete_runs_the_gate_process_and_tells_the_driver(svc):
    aid = book(svc, 1)
    assert svc.check_in(aid).status == "ARRIVED"
    assert svc.live(aid, now=NOW)["phase"] == "at_gate"
    assert svc.complete(aid).status == "COMPLETED"
    live = svc.live(aid, now=NOW)
    assert live["phase"] == "completed" and "may leave" in live["next_step"]
    assert [e["event_type"] for e in svc.events(aid)][-2:] == ["ARRIVED", "COMPLETED"]
    assert svc.notifications(aid)[0]["title"] == "Gate process complete"


def test_the_gate_process_cannot_be_skipped_or_repeated(svc):
    waiting = book(svc, 1, approve=False)
    with pytest.raises(BookingError):
        svc.check_in(waiting)  # not approved
    with pytest.raises(BookingError):
        svc.complete(waiting)
    aid = book(svc, 2)
    svc.complete(aid)  # a quick desk may complete straight from approved
    with pytest.raises(BookingError):
        svc.complete(aid)
    with pytest.raises(BookingError):
        svc.cancel(aid)  # too late to cancel


def test_no_show_releases_the_place(svc):
    aid = book(svc, 1)
    assert svc.mark_no_show(aid).status == "NO_SHOW"
    assert svc.live(aid, now=NOW)["phase"] == "no_show"
    with pytest.raises(BookingError):
        svc.check_in(aid)


def test_a_truck_at_the_gate_still_counts_but_a_finished_one_frees_the_lane(svc):
    aid = book(svc, 1)
    slot = svc.repo.get(aid).assigned_slot
    lane = svc.repo.get(aid).lane
    base = svc._lane_loads(slot)[1][lane]
    svc.check_in(aid)
    assert svc._lane_loads(slot)[1][lane] == base  # still queued at its lane
    svc.complete(aid)
    assert svc._lane_loads(slot)[1][lane] < base


def test_trucks_at_the_gate_are_not_moved_to_another_lane(svc):
    aid = book(svc, 1)
    lane = svc.repo.get(aid).lane
    svc.check_in(aid)
    svc.close_lane(lane, hours=3, start=f"{DATE}T10:00", reason="crane breakdown", now=NOW)
    assert svc.repo.get(aid).lane == lane  # the officer is already processing it


def test_the_desk_shows_the_uploaded_documents_and_what_is_missing(svc):
    aid = book(svc, 1)
    lane = svc.repo.get(aid).lane
    docs = svc.gate_desk(lane, DATE, now=NOW)["bookings"][0]["document_summary"]
    assert docs["total"] == 6 and docs["cleared"] == 0 and {d["status"] for d in docs["documents"]} == {"missing"}

    svc._doc_results[aid] = {
        "vgm": {
            "status": "flagged", "filename": "vgm.png", "ocr_confidence": 0.87, "customs_assessment": None,
            "issues": [{"level": "error", "code": "container_mismatch", "message": "Container number does not match the booking."}],
            "fields": {"booking_no": "AAA111"},
            "template": {"completeness": 0.75, "fields": [{"label": "Container number", "value": "MSKU1234565", "status": "ok", "required": True}]},
        },
        "booking_confirmation": {"status": "cleared", "filename": "b.png", "ocr_confidence": 0.9, "issues": [], "fields": {"booking_no": "AAA111", "vessel_name": "MV EVER GRACE"}, "template": None},
        "cusdec": {"status": "cleared", "filename": "c.png", "ocr_confidence": 0.9, "issues": [], "fields": {}, "template": None},
    }
    docs = svc.gate_desk(lane, DATE, now=NOW)["bookings"][0]["document_summary"]
    by_key = {d["doc_key"]: d for d in docs["documents"]}
    assert docs["cleared"] == 2 and by_key["gate_pass"]["status"] == "missing"
    assert by_key["vgm"]["status"] == "flagged" and by_key["vgm"]["filename"] == "vgm.png"
    assert by_key["vgm"]["details"][0]["value"] == "MSKU1234565" and by_key["vgm"]["issues"][0]["level"] == "error"
    assert by_key["booking_confirmation"]["status"] == "cleared"


def test_the_desk_lists_documents_that_disagree_with_each_other(svc):
    aid = book(svc, 1)
    svc._doc_results[aid] = {
        "booking_confirmation": {"status": "cleared", "issues": [], "fields": {"booking_no": "MLKBC2609187"}, "template": None},
        "vgm": {"status": "cleared", "issues": [], "fields": {"booking_no": "MEDKSL2609187"}, "template": None},
    }
    b = svc.gate_desk(svc.repo.get(aid).lane, DATE, now=NOW)["bookings"][0]
    assert [c["code"] for c in b["document_summary"]["cross_checks"]] == ["booking_no_differs"]


def test_desk_rejects_an_unknown_gate_or_date(svc):
    with pytest.raises(BookingError):
        svc.gate_desk(9, DATE)
    with pytest.raises(BookingError):
        svc.gate_desk(1, "07/01/2030")


def test_gate_desk_endpoints():
    import main

    with TestClient(main.app) as client:
        body = dict(truck_id="TRK-DESK", container_id="CSQU3054383", carrier="Carrier-A", cargo_category="export",
                    container_type="standard", arrival_date="2031-03-04", arrival_hour=10)
        a = client.post("/api/appointments", json=body).json()["appointment"]
        assert client.post(f"/api/appointments/{a['id']}/check-in").status_code == 422  # not approved yet
        client.post(f"/api/appointments/{a['id']}/approve")
        desk = client.get(f"/api/gates/{a['lane']}/desk?date=2031-03-04").json()
        assert a["id"] in [b["id"] for b in desk["bookings"]]
        assert client.post(f"/api/appointments/{a['id']}/check-in").json()["status"] == "ARRIVED"
        assert client.post(f"/api/appointments/{a['id']}/complete").json()["status"] == "COMPLETED"
        assert client.get("/api/gates/9/desk").status_code == 422
