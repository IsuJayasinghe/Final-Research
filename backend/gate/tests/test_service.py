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
    assert [e["event_type"] for e in svc.events(1)] == ["ASSIGNED", "APPROVED", "CANCELLED"]


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
    from doc_fixtures import make_samples

    return make_samples(tmp_path_factory.mktemp("docs"), DATE)  # documents are dated for the appointment they are checked against


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


# ---- documents unknown at booking, established by OCR afterwards ----------------------------------

def booking_without_documents(svc, i=1, **kw):
    base = dict(container_id="CSQU3054383", truck_id="TRK-80579", container_type="hazardous",
                carrier="Carrier-B", carrier_reliability=0.54, arrival_date=DATE, arrival_hour=10)
    base.update(kw)
    r = req(i, **base)
    r.pop("customs_risk_flag")
    r.pop("missing_documents")
    return svc.create(r, now=EARLY)


def test_booking_without_documents_is_estimated_not_assumed_clean(svc):
    out = booking_without_documents(svc)
    a = out["appointment"]
    assert a["customs_risk_flag"] is None and a["missing_documents"] is None
    assert out["risk"]["documents_known"] is False and "not checked yet" in a["risk_summary"]
    assert a["predicted_clearance_minutes"] > 0 and a["lane"] in range(1, 7)
    known_clean = svc.create(req(2, hour=10, container_id="CSQU3054383", customs_risk_flag="low", missing_documents=0,
                                 carrier="Carrier-B", carrier_reliability=0.54, container_type="hazardous"), now=EARLY)
    assert known_clean["appointment"]["p_no_show"] < a["p_no_show"]  # a verified-clean set is better than a guess


@ocr_needed
@pytest.mark.parametrize("cusdec_name,level", [("cusdec_low_risk", "low"), ("cusdec", "medium"), ("cusdec_high_risk", "high")])
def test_customs_risk_comes_from_the_uploaded_customs_document(svc, sample_dir, cusdec_name, level):
    aid = booking_without_documents(svc)["appointment"]["id"]
    for name, slot in SLOTS.items():
        upload(svc, sample_dir, aid, cusdec_name if slot == "cusdec" else name, slot)
    out = svc.submit_documents(aid)
    assert out["before"]["customs_risk"] is None and out["after"]["customs_risk"] == level
    assert out["customs_assessment"]["level"] == level and out["missing"] == 0
    assert svc.repo.get(aid).customs_risk_flag == level and svc.repo.get(aid).missing_documents == 0


@ocr_needed
def test_riskier_customs_document_gives_higher_no_show_risk(svc, sample_dir):
    risks = {}
    for i, name in enumerate(("cusdec_low_risk", "cusdec_high_risk"), start=1):
        aid = booking_without_documents(svc, i=i, truck_id=f"TRK-{i}")["appointment"]["id"]
        for doc, slot in SLOTS.items():
            upload(svc, sample_dir, aid, name if slot == "cusdec" else doc, slot)
        risks[name] = svc.submit_documents(aid)["after"]["p_no_show"]
    assert risks["cusdec_low_risk"] < risks["cusdec_high_risk"]


@ocr_needed
def test_without_a_customs_document_customs_risk_stays_unknown(svc, sample_dir):
    aid = booking_without_documents(svc)["appointment"]["id"]
    upload(svc, sample_dir, aid, "vgm", "vgm")
    out = svc.submit_documents(aid)
    assert out["after"]["customs_risk"] is None and out["customs_assessment"] is None
    assert svc.repo.get(aid).customs_risk_flag is None and out["missing"] == 6


# ---- weather, carrier reliability and vessel delay are automatic ---------------------------------------

import weather as weather_module  # noqa: E402


def bare_booking(svc, i=1, **kw):
    """A booking with only what a person knows: who, what, when. Everything else must be derived."""
    base = dict(
        truck_id=f"TRK-{i}", container_id="CSQU3054383", carrier="Carrier-B", cargo_category="export",
        container_type="hazardous", arrival_date=DATE, arrival_hour=10,
    )
    base.update(kw)
    return svc.create(base, now=EARLY)


def test_carrier_reliability_comes_from_the_carriers_history(svc):
    b = bare_booking(svc)
    j = bare_booking(svc, i=2, carrier="Carrier-J")
    assert 0.45 < b["appointment"]["carrier_reliability"] < 0.6  # the unreliable carrier
    assert j["appointment"]["carrier_reliability"] > 0.8
    assert b["conditions"]["carrier"]["past_no_show_rate"] > j["conditions"]["carrier"]["past_no_show_rate"]
    assert b["appointment"]["p_no_show"] > j["appointment"]["p_no_show"]
    # an explicit value still wins (simulations / what-if)
    assert bare_booking(svc, i=3, carrier_reliability=0.9)["appointment"]["carrier_reliability"] == 0.9


def test_weather_comes_from_the_forecast(svc, monkeypatch):
    seen = []

    def forecast(day):
        seen.append(day)
        return {"date": day, "severity": 2, "label": "Heavy rain", "source": "open-meteo"}

    monkeypatch.setattr(weather_module, "get_weather", forecast)
    out = bare_booking(svc)
    assert seen == [DATE]
    assert out["appointment"]["weather_severity"] == 2 and out["appointment"]["weather_source"] == "open-meteo"
    assert out["conditions"]["weather"]["label"] == "Heavy rain" and out["risk"]["weather_known"] is True


def test_stormier_forecast_means_higher_no_show_risk(svc, monkeypatch):
    risks = {}
    for severity in (0, 3):
        monkeypatch.setattr(weather_module, "get_weather",
                            lambda day, s=severity: {"date": day, "severity": s, "label": "x", "source": "open-meteo"})
        risks[severity] = bare_booking(svc, i=severity + 1)["appointment"]["p_no_show"]
    assert risks[0] < risks[3]


def test_unavailable_forecast_is_unknown_and_says_so(svc):
    out = bare_booking(svc)  # conftest makes the weather API unreachable
    a = out["appointment"]
    assert a["weather_severity"] is None and a["weather_source"] in ("unavailable", "beyond-forecast-range")
    assert out["risk"]["weather_known"] is False and "weather forecast unavailable" in a["risk_summary"].lower()


def test_entered_weather_is_still_accepted_and_labelled(svc):
    out = bare_booking(svc, weather_severity=1)
    assert out["appointment"]["weather_severity"] == 1 and out["appointment"]["weather_source"] == "entered"


@ocr_needed
@pytest.mark.parametrize("booking_doc,delayed,hours", [("booking_confirmation", False, 0.0), ("booking_confirmation_delayed_vessel", True, 5.0)])
def test_vessel_delay_is_read_from_the_booking_confirmation(svc, sample_dir, booking_doc, delayed, hours):
    aid = bare_booking(svc)["appointment"]["id"]
    assert svc.repo.get(aid).vessel_delay is None  # unknown until the booking confirmation is read
    for name, slot in SLOTS.items():
        upload(svc, sample_dir, aid, booking_doc if slot == "booking_confirmation" else name, slot)
    out = svc.submit_documents(aid)
    a = svc.repo.get(aid)
    assert out["before"]["vessel_delay"] is None and out["after"]["vessel_delay"] is delayed
    assert a.vessel_delay is delayed and a.vessel_delay_hours == hours
    assert a.vessel_name == ("MV OCEAN PIONEER" if delayed else "MV EVER GRACE")
    assert out["vessel"]["source"].startswith("simulated")
    assert (f"delayed {hours:g} h" in out["summary"]) if delayed else ("on schedule" in out["summary"])


@ocr_needed
def test_a_delayed_vessel_raises_no_show_risk(svc, sample_dir):
    risks = {}
    for i, doc in enumerate(("booking_confirmation", "booking_confirmation_delayed_vessel"), start=1):
        aid = bare_booking(svc, i=i)["appointment"]["id"]
        for name, slot in SLOTS.items():
            upload(svc, sample_dir, aid, doc if slot == "booking_confirmation" else name, slot)
        risks[doc] = svc.submit_documents(aid)["after"]["p_no_show"]
    assert risks["booking_confirmation"] < risks["booking_confirmation_delayed_vessel"]


@ocr_needed
def test_vessel_stays_unknown_without_a_booking_confirmation(svc, sample_dir):
    aid = bare_booking(svc)["appointment"]["id"]
    upload(svc, sample_dir, aid, "vgm", "vgm")
    out = svc.submit_documents(aid)
    assert out["vessel"] is None and svc.repo.get(aid).vessel_delay is None


@ocr_needed
def test_submit_reports_how_complete_each_document_is(svc, sample_dir):
    aid = bare_booking(svc, truck_id="TRK-80579")["appointment"]["id"]  # the truck named on the sample gate pass
    for name, slot in SLOTS.items():
        upload(svc, sample_dir, aid, "booking_confirmation_incomplete" if slot == "booking_confirmation" else name, slot)
    out = svc.submit_documents(aid)
    by_key = {r["doc_key"]: r for r in out["required"]}
    assert by_key["booking_confirmation"]["status"] == "flagged"
    assert 0 < by_key["booking_confirmation"]["completeness"] < 1
    assert {"Voyage number", "Port of discharge"} <= set(by_key["booking_confirmation"]["missing_details"])
    assert by_key["vgm"]["completeness"] == 1.0 and by_key["vgm"]["missing_details"] == []
    flagged = {k: (r["status"], r["missing_details"]) for k, r in by_key.items() if r["status"] != "cleared"}
    assert out["missing"] == 1, flagged  # only the incomplete booking confirmation fails
    stored = __import__("json").loads(svc.repo.submissions(aid)[0]["clearance_information"])
    assert stored["completeness"]["vgm"] == 1.0 and "booking_confirmation" in stored["missing_details"]


# ---- lane allocation spreads a busy hour across the lanes ----------------------------------------------------

def test_bookings_in_one_hour_spread_across_lanes_instead_of_piling_onto_one(svc):
    lanes = [bare_booking(svc, i=i, truck_id=f"TRK-{i}")["appointment"]["lane"] for i in range(1, 7)]
    assert len(set(lanes)) >= 4, lanes  # six trucks in the same hour do not all get the same lane
    one_lane = max(lanes.count(x) for x in set(lanes))
    assert one_lane <= 2


def test_first_booking_still_gets_the_quietest_lane(svc):
    first = bare_booking(svc)
    forecasts = {l["lane"]: l["predicted_queue_length"] for l in first["lanes"]}
    assert first["appointment"]["lane"] == min(forecasts, key=lambda ln: (forecasts[ln], ln))


def test_a_cancelled_booking_frees_its_lane_slot(svc):
    ids = [bare_booking(svc, i=i, truck_id=f"TRK-{i}")["appointment"] for i in range(1, 4)]
    taken = ids[0]["lane"]
    svc.cancel(ids[0]["id"])
    again = bare_booking(svc, i=9, truck_id="TRK-9")["appointment"]["lane"]
    assert again == taken  # the lane is free again, so it is the quietest choice once more


# ---- gate monitoring: hourly busy profile and per-lane view ------------------------------------------------

def test_profile_shows_quiet_nights_and_a_congested_afternoon(svc):
    rows = svc.congestion_profile(DATE)
    assert [r["hour"] for r in rows] == list(range(24))
    by_hour = {r["hour"]: r for r in rows}
    assert by_hour[3]["status"] == "normal" and by_hour[3]["max_lane_queue"] < 4
    assert by_hour[16]["status"] == "congested" and by_hour[16]["max_lane_queue"] >= 8
    assert by_hour[16]["avg_wait_minutes"] > by_hour[3]["avg_wait_minutes"] * 5
    peak = max(rows, key=lambda r: r["max_lane_queue"])
    assert 12 <= peak["hour"] <= 18  # the busy period of the day


def test_status_thresholds():
    from service import lane_status

    assert [lane_status(q) for q in (0, 3.9, 4, 7.9, 8, 15)] == ["normal", "normal", "busy", "busy", "congested", "congested"]


def test_lane_view_lists_the_real_bookings_on_each_lane(svc):
    made = [bare_booking(svc, i=i, truck_id=f"TRK-{i}")["appointment"] for i in range(1, 5)]
    slot = made[0]["assigned_slot"]
    view = svc.lane_view(slot[:10], int(slot[11:13]))
    assert view["booked_total"] == 4 and len(view["lanes"]) == 6
    listed = {b["id"] for lane in view["lanes"] for b in lane["bookings"]}
    assert listed == {a["id"] for a in made}
    for lane in view["lanes"]:
        assert all(b["lane"] == lane["lane"] for b in lane["bookings"])
        assert lane["status"] in ("normal", "busy", "congested")


def test_lane_view_ignores_cancelled_and_other_hours(svc):
    a = bare_booking(svc)["appointment"]
    slot = a["assigned_slot"]
    svc.cancel(a["id"])
    assert svc.lane_view(slot[:10], int(slot[11:13]))["booked_total"] == 0
    assert svc.lane_view(slot[:10], (int(slot[11:13]) + 5) % 24)["booked_total"] == 0


def test_a_disruption_raises_the_queues_the_monitor_shows(svc):
    before = svc.lane_view(DATE, 10)
    assert before["disruption"] is None
    svc.reoptimize(vessel_delay_hours=4, queue_spike_pct=100, window_hours=2, start=f"{DATE}T10:00", now=EARLY)
    after = svc.lane_view(DATE, 10)
    assert after["disruption"]["uplift_pct"] == 160  # +60% vessel delay, +100% queue spike
    for b, a in zip(before["lanes"], after["lanes"]):
        assert a["predicted_queue_length"] > b["predicted_queue_length"] * 2.4
    assert svc.lane_view(DATE, 13)["disruption"] is None  # outside the disrupted window
    row = {r["hour"]: r for r in svc.congestion_profile(DATE)}
    assert row[10]["disrupted"] is True and row[13]["disrupted"] is False
    assert row[10]["status"] == "congested"


def test_monitor_rejects_bad_dates_and_hours(svc):
    with pytest.raises(BookingError):
        svc.lane_view("nonsense", 10)
    with pytest.raises(BookingError):
        svc.lane_view(DATE, 25)
    with pytest.raises(BookingError):
        svc.congestion_profile("2030-13-45")


# ---- gate-admin approval: the driver waits, documents unlock only after approval -------------------------------

@pytest.fixture
def strict():
    """The running app's configuration: documents need an approved appointment."""
    return GateService(MemoryRepository(), require_approval=True)


def test_a_new_request_waits_for_the_gate_admin(strict):
    a = bare_booking(strict)["appointment"]
    assert a["status"] == "PENDING"  # awaiting approval
    assert strict.repo.events(a["id"])[0]["event_type"] == "ASSIGNED"


def test_documents_are_locked_until_the_gate_admin_approves(strict):
    aid = bare_booking(strict)["appointment"]["id"]
    with pytest.raises(BookingError, match="gate admin approves"):
        strict.check_document(b"x", "a.png", "vgm", appointment_id=aid)
    with pytest.raises(BookingError, match="waiting for the gate admin"):
        strict.submit_documents(aid)
    strict.approve(aid)
    # past the gate: the (bad) file is now judged on its content instead of being refused for approval
    with pytest.raises(documents.DocumentError):
        strict.check_document(b"x", "a.png", "vgm", appointment_id=aid)


def test_approval_fixes_the_slot_and_logs_an_event(strict):
    aid = bare_booking(strict)["appointment"]["id"]
    a = strict.approve(aid, note="Looks fine.")
    assert a.status == "CONFIRMED"
    event = strict.repo.events(aid)[-1]
    assert event["event_type"] == "APPROVED" and "Looks fine." in event["reason"] and "upload your documents" in event["reason"].lower()
    with pytest.raises(BookingError):
        strict.approve(aid)  # already approved


def test_rejected_request_frees_the_slot_and_shows_the_reason(strict):
    first = bare_booking(strict)["appointment"]
    slot = first["assigned_slot"]
    out = strict.reject(first["id"], "Gate closed for maintenance in that hour.")
    assert out.status == "REJECTED" and "maintenance" in out.decision_reason
    assert strict.repo.events(first["id"])[-1]["event_type"] == "REJECTED"
    assert strict.lane_view(slot[:10], int(slot[11:13]))["booked_total"] == 0  # no longer counts against the slot
    with pytest.raises(BookingError, match="gate admin has rejected|rejected by the gate admin"):
        strict.check_document(b"x", "a.png", "vgm", appointment_id=first["id"])
    with pytest.raises(BookingError):
        strict.approve(first["id"])  # a rejected request cannot be approved afterwards


def test_a_blank_rejection_reason_still_says_something(strict):
    aid = bare_booking(strict)["appointment"]["id"]
    assert "No reason given" in strict.reject(aid).decision_reason


def test_cancelled_appointments_cannot_be_approved_or_rejected(strict):
    aid = bare_booking(strict)["appointment"]["id"]
    strict.cancel(aid)
    with pytest.raises(BookingError):
        strict.approve(aid)
    with pytest.raises(BookingError):
        strict.reject(aid, "x")


def test_a_driver_can_look_up_only_their_own_truck(strict):
    bare_booking(strict, i=1, truck_id="TRK-111")
    bare_booking(strict, i=2, truck_id="TRK-222")
    mine = strict.list(truck_id=" trk-111 ")
    assert [a["truck_id"] for a in mine] == ["TRK-111"]
    assert len(strict.list()) == 2 and strict.list(statuses=["CONFIRMED"]) == []
