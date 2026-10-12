from datetime import datetime

import pytest

import ml_models
import noshow
import scheduler
from repository import MemoryRepository
from service import BookingError, GateService

NOW = datetime(2030, 1, 7, 6, 30)
DATE = "2030-01-07"


@pytest.fixture(scope="module", autouse=True)
def _models():
    ml_models.load_models()
    noshow.load_model()


@pytest.fixture
def svc():
    return GateService(MemoryRepository())


def req(i=1, risky=False, hour=9, **kw):
    base = dict(
        truck_id=f"TRK-{i}",
        container_id=f"MAEU{i:07d}",
        carrier="Carrier-B" if risky else "Carrier-J",
        cargo_category="export",
        container_type="hazardous" if risky else "standard",
        customs_risk_flag="high" if risky else "low",
        missing_documents=3 if risky else 0,
        carrier_reliability=0.54 if risky else 0.87,
        arrival_date=DATE,
        arrival_hour=hour,
        weather_severity=2 if risky else 0,
        vessel_delay=risky,
    )
    base.update(kw)
    return base


def test_create_saves_booking_with_risk_lane_and_reasons(svc):
    out = svc.create(req(1, risky=True), now=NOW)
    a = out["appointment"]
    assert a["id"] == 1 and a["status"] == "PENDING"
    assert a["lane"] in range(1, 7) and a["predicted_clearance_minutes"] > 0
    assert out["risk"]["p_no_show"] > 0.15 and out["risk"]["drivers"]
    assert out["decision"]["reason"] and out["timing"]["gate_entry"] <= out["timing"]["departure"]
    assert len(out["lanes"]) == 6
    assert svc.repo.events(1)[0]["event_type"] == "ASSIGNED"


def test_rejects_past_or_missing_time(svc):
    with pytest.raises(BookingError):
        svc.create(req(1, arrival_date="2029-12-31"), now=NOW)
    with pytest.raises(BookingError):
        svc.create(req(1, arrival_date=None), now=NOW)


def test_risky_bookings_can_overbook_a_full_slot(svc):
    results = [svc.create(req(i, risky=True), now=NOW) for i in range(1, 9)]
    slots = {}
    for r in results:
        slots.setdefault(r["appointment"]["assigned_slot"], []).append(r)
    busiest = max(slots.values(), key=len)
    assert len(busiest) > scheduler.SLOT_CAPACITY  # more bookings than capacity ...
    assert any(r["appointment"]["overbooked"] for r in busiest)  # ... flagged as overbooked
    assert len(busiest) <= scheduler.SLOT_CAPACITY + scheduler.MAX_OVERBOOK  # ... but capped


def test_dependable_bookings_are_not_overbooked(svc):
    results = [svc.create(req(i), now=NOW) for i in range(1, 12)]
    per_slot = {}
    for r in results:
        a = r["appointment"]
        per_slot[a["assigned_slot"]] = per_slot.get(a["assigned_slot"], 0) + 1
        assert not a["overbooked"]
    assert max(per_slot.values()) <= scheduler.SLOT_CAPACITY


def test_confirm_and_cancel_lifecycle(svc):
    svc.create(req(1), now=NOW)
    assert svc.confirm(1).status == "CONFIRMED"
    with pytest.raises(BookingError):
        svc.confirm(1)  # only PENDING can be confirmed
    assert svc.cancel(1).status == "CANCELLED"
    with pytest.raises(BookingError):
        svc.cancel(1)
    with pytest.raises(BookingError):
        svc.confirm(99)
    assert [e["event_type"] for e in svc.events(1)] == ["ASSIGNED", "CONFIRMED", "CANCELLED"]


def test_cancelled_booking_frees_capacity(svc):
    for i in range(1, 7):
        svc.create(req(i), now=NOW)
    board = {r["slot"]: r for r in svc.slot_board(DATE)}
    full_slot = max(board.values(), key=lambda r: r["bookings"])
    assert full_slot["bookings"] == 6
    svc.cancel(1)
    board = {r["slot"]: r for r in svc.slot_board(DATE)}
    assert board[full_slot["slot"]]["bookings"] == 5


# A booking keeps its requested hour unless a slot is full or the saving is real, so at 09:30 a
# 10:00 request stays at 10:00 (about 34 min forecast wait) until a disruption makes that hour expensive.
EARLY = datetime(2030, 1, 7, 9, 30)


def test_booking_keeps_requested_hour_when_nothing_is_wrong(svc):
    out = svc.create(req(1, hour=10), now=EARLY)
    assert out["appointment"]["assigned_slot"].endswith("10:00")
    assert "requested slot" in out["decision"]["reason"]


def test_reoptimize_fixes_confirmed_and_explains_every_move(svc):
    for i in range(1, 6):
        svc.create(req(i, hour=10, risky=(i % 2 == 0)), now=EARLY)
    svc.confirm(1)
    before = {a["id"]: a["assigned_slot"] for a in svc.list()}
    assert before[2].endswith("10:00")

    out = svc.reoptimize(vessel_delay_hours=4, queue_spike_pct=0, window_hours=1, now=EARLY)

    after = {a["id"]: a["assigned_slot"] for a in svc.list()}
    assert after[1] == before[1]  # the confirmed booking never moves
    assert out["considered"] == 4 and out["fixed_confirmed"] == 1
    assert out["moved"] == 4  # every unconfirmed booking leaves the disrupted 10:00 hour
    assert all(not after[i].endswith("10:00") for i in range(2, 6))
    assert out["expected_wait_after_min"] < out["expected_wait_before_min"]
    for ch in out["changes"]:
        assert "vessel delay of 4h" in ch["reasons"][0] and "%" in ch["reasons"][0]
        assert any(r.startswith("Moved to") for r in ch["reasons"])
    assert [e["event_type"] for e in svc.repo.events(2)] == ["ASSIGNED", "REASSIGNED"]
    assert "No-show risk" in " ".join(out["changes"][0]["reasons"])  # risky booking cites its risk


def test_new_bookings_respect_an_active_disruption(svc):
    svc.reoptimize(vessel_delay_hours=4, window_hours=1, now=EARLY)  # 10:00 becomes ~3.6x more congested
    during = svc.create(req(2, hour=10), now=EARLY)["appointment"]["assigned_slot"]
    assert not during.endswith("10:00")
    svc.clear_disruption()
    assert svc.create(req(3, hour=10), now=EARLY)["appointment"]["assigned_slot"].endswith("10:00")


def test_disruption_can_target_a_future_window(svc):
    long_before = datetime(2030, 1, 1, 8, 0)
    for i in range(1, 4):
        svc.create(req(i, hour=10), now=long_before)
    assert svc.repo.get(1).assigned_slot.hour == 10
    out = svc.reoptimize(vessel_delay_hours=4, window_hours=1, start="2030-01-07T10:00", now=long_before)
    assert out["disruption"]["window_start"] == "2030-01-07T10:00" and out["moved"] == 3
    assert all(svc.repo.get(i).assigned_slot.hour != 10 for i in (1, 2, 3))


def test_bad_disruption_start_is_rejected(svc):
    with pytest.raises(BookingError):
        svc.reoptimize(vessel_delay_hours=2, start="tomorrow-ish", now=EARLY)


# ---- OCR document checking feeds back into the booking ------------------------------------

import documents  # noqa: E402

ocr_needed = pytest.mark.skipif(not documents.ocr_available(), reason="rapidocr_onnxruntime not installed")
SLOTS = {
    "booking_confirmation": "booking_confirmation",
    "cusdec": "cusdec",
    "gate_pass": "gate_pass",
    "vgm": "vgm",
    "seal_photo": "seal_match",
    "driver_docs": "driver_docs",
    "special_cargo": "special_cargo",
}


@pytest.fixture(scope="module")
def sample_dir(tmp_path_factory):
    from tools import make_sample_documents as gen

    out = tmp_path_factory.mktemp("docs")
    gen.main(out)
    return out


def doc_booking(svc, **kw):
    """A hazardous booking for the container/truck printed on the sample documents."""
    base = dict(
        container_id="CSQU3054383",
        truck_id="TRK-80579",
        container_type="hazardous",
        carrier="Carrier-B",
        carrier_reliability=0.54,
        customs_risk_flag="high",
        missing_documents=3,
        arrival_date=DATE,
        arrival_hour=10,
    )
    base.update(kw)
    return svc.create(req(1, **base), now=EARLY)["appointment"]["id"]


def upload(svc, sample_dir, appointment_id, name, slot):
    path = sample_dir / f"{name}.png"
    return svc.check_document(path.read_bytes(), path.name, slot, appointment_id=appointment_id)


@ocr_needed
def test_complete_clean_documents_lower_risk_and_clear_missing_count(svc, sample_dir):
    aid = doc_booking(svc)
    for name, slot in SLOTS.items():
        assert upload(svc, sample_dir, aid, name, slot)["status"] == "cleared", name

    out = svc.submit_documents(aid)
    assert out["missing"] == 0 and out["cleared"] == 7
    assert out["before"]["missing_documents"] == 3 and out["after"]["missing_documents"] == 0
    assert out["after"]["p_no_show"] < out["before"]["p_no_show"]
    assert out["after"]["clearance_minutes"] < out["before"]["clearance_minutes"]
    saved = svc.repo.get(aid)
    assert saved.missing_documents == 0 and saved.p_no_show == out["after"]["p_no_show"]
    assert svc.repo.events(aid)[-1]["event_type"] == "DOCUMENTS_CHECKED"
    sub = svc.repo.submissions(aid)[0]
    assert "CSQU3054383" in sub["cargo_details"] and "SL884213" in sub["cargo_details"]
    assert "WP CAB-1234" in sub["vehicle_details"]


@ocr_needed
def test_flagged_and_unuploaded_documents_count_as_missing(svc, sample_dir):
    aid = doc_booking(svc, missing_documents=0)
    assert upload(svc, sample_dir, aid, "vgm_wrong_container", "vgm")["status"] == "flagged"
    assert upload(svc, sample_dir, aid, "booking_confirmation", "booking_confirmation")["status"] == "cleared"
    out = svc.submit_documents(aid)
    assert out["cleared"] == 1 and out["missing"] == 6
    assert out["after"]["p_no_show"] > out["before"]["p_no_show"]  # more missing paperwork -> higher risk
    statuses = {r["doc_key"]: r["status"] for r in out["required"]}
    assert statuses["vgm"] == "flagged" and statuses["cusdec"] == "missing"
    assert "container_mismatch" in {i["code"] for i in out["issues"]["vgm"]}


@ocr_needed
def test_booking_supplies_the_expected_container(svc, sample_dir):
    aid = doc_booking(svc, container_id="MSKU1234565")  # booked a different container than the documents show
    assert upload(svc, sample_dir, aid, "vgm", "vgm")["status"] == "flagged"


def test_document_submission_guards(svc):
    with pytest.raises(BookingError):
        svc.check_document(b"x", "a.png", "vgm", appointment_id=99)
    aid = doc_booking(svc)
    with pytest.raises(BookingError):
        svc.submit_documents(aid)  # nothing checked yet
    svc._doc_results[aid] = {"vgm": {"status": "cleared", "fields": {}, "issues": []}}
    svc.cancel(aid)
    with pytest.raises(BookingError):
        svc.submit_documents(aid)
