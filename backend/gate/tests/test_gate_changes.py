"""Automatic gate (lane) changes, delay notices and the driver's live view."""

from datetime import datetime

import pytest

import ml_models
import noshow
from repository import MemoryRepository
from service import BookingError, GateService

DATE = "2030-01-07"
NOW = datetime(2030, 1, 7, 6, 30)  # the booked day is in the future
SLOT10 = f"{DATE}T10:00"


@pytest.fixture(scope="module", autouse=True)
def _models():
    ml_models.load_models()
    noshow.load_model()


@pytest.fixture
def svc():
    return GateService(MemoryRepository(), require_approval=True)


def book(svc, i, hour=10, **kw):
    req = dict(truck_id=f"TRK-{i}", container_id="CSQU3054383", carrier="Carrier-A", cargo_category="export",
               container_type="standard", arrival_date=DATE, arrival_hour=hour, weather_severity=0, vessel_delay=False)
    req.update(kw)
    return svc.create(req, now=NOW)["appointment"]


def lane_of(svc, aid):
    return svc.repo.get(aid).lane


# ---- lane closures ------------------------------------------------------------------------------------

def test_closing_a_lane_moves_its_drivers_to_another_gate_and_tells_them(svc):
    a = book(svc, 1)
    svc.approve(a["id"])
    old_lane, slot_before = a["lane"], svc.repo.get(a["id"]).assigned_slot
    out = svc.close_lane(old_lane, hours=3, start=SLOT10, reason="crane breakdown", now=NOW)
    assert [c["appointment_id"] for c in out["lane_changes"]] == [a["id"]]
    moved = svc.repo.get(a["id"])
    assert moved.lane != old_lane and moved.status == "CONFIRMED"  # still approved
    assert moved.assigned_slot == slot_before  # the time does not change, only the gate
    note = svc.notifications(a["id"])[0]
    assert note["type"] == "LANE_CHANGED" and note["level"] == "warning"
    assert f"Gate {old_lane} is closed (crane breakdown)" in note["message"] and f"Gate {moved.lane}" in note["message"]


def test_drivers_on_other_lanes_are_left_alone(svc):
    a, b = book(svc, 1), book(svc, 2)
    assert a["lane"] != b["lane"]
    svc.close_lane(a["lane"], hours=2, start=SLOT10, now=NOW)
    assert lane_of(svc, b["id"]) == b["lane"]
    assert [e["event_type"] for e in svc.repo.events(b["id"])] == ["ASSIGNED"]


def test_new_bookings_never_get_a_closed_lane(svc):
    first = book(svc, 1)
    svc.close_lane(first["lane"], hours=3, start=SLOT10, now=NOW)
    booked = [svc.repo.get(book(svc, i)["id"]) for i in range(2, 9)]
    in_window = [a for a in booked if a.assigned_slot.hour in (10, 11, 12)]
    assert in_window  # most of these land in the closure window
    assert all(a.lane != first["lane"] for a in in_window)


def test_the_last_open_lane_cannot_be_closed(svc):
    for lane in range(1, 6):
        svc.close_lane(lane, hours=2, start=SLOT10, now=NOW)
    with pytest.raises(BookingError, match="(?i)at least one lane"):
        svc.close_lane(6, hours=2, start=SLOT10, now=NOW)
    svc.close_lane(6, hours=1, start=f"{DATE}T13:00", now=NOW)  # a different hour still has open lanes


def test_a_closure_only_affects_its_own_window(svc):
    a = book(svc, 1, hour=10)
    c = book(svc, 2, hour=14)
    svc.close_lane(a["lane"], hours=1, start=SLOT10, now=NOW)
    assert svc.lane_view(DATE, 14)["lanes"][c["lane"] - 1]["status"] != "closed"
    assert svc.lane_view(DATE, 10)["lanes"][a["lane"] - 1]["status"] == "closed"


def test_reopening_a_lane_makes_it_available_again(svc):
    first = book(svc, 1)
    lane = first["lane"]
    svc.close_lane(lane, hours=2, start=SLOT10, now=NOW)
    assert svc.list_closures()[0]["lane"] == lane
    assert svc.reopen_lane(lane) == {"reopened": 1} and svc.list_closures() == []
    assert svc.lane_view(DATE, 10)["lanes"][lane - 1]["status"] != "closed"


def test_invalid_closures_are_rejected(svc):
    with pytest.raises(BookingError):
        svc.close_lane(9, now=NOW)
    with pytest.raises(BookingError):
        svc.close_lane(2, hours=0, now=NOW)
    with pytest.raises(BookingError):
        svc.close_lane(2, hours=2, start="not-a-time", now=NOW)


def test_the_monitor_shows_closed_lanes_and_the_profile_ignores_them(svc):
    svc.close_lane(3, hours=2, start=SLOT10, reason="maintenance", now=NOW)
    lane = svc.lane_view(DATE, 10)["lanes"][2]
    assert lane["status"] == "closed" and lane["closed_reason"] == "maintenance" and lane["predicted_queue_length"] is None
    open_lanes = [ln for ln in svc.lane_view(DATE, 10)["lanes"] if ln["status"] != "closed"]
    assert len(open_lanes) == 5
    row = svc.congestion_profile(DATE)[10]
    assert row["max_lane_queue"] == max(ln["predicted_queue_length"] for ln in open_lanes)


# ---- lane-specific disruptions move drivers off the hit lane ---------------------------------------------------

def test_a_queue_spike_on_one_gate_moves_drivers_to_a_lighter_one(svc):
    a = book(svc, 1)
    svc.approve(a["id"])
    hit = a["lane"]
    out = svc.reoptimize(queue_spike_pct=300, window_hours=1, start=SLOT10, lane=hit, now=NOW)
    assert [c["appointment_id"] for c in out["lane_changes"]] == [a["id"]]
    assert lane_of(svc, a["id"]) != hit
    assert out["disruption"]["lane"] == hit
    assert "became congested" in out["lane_changes"][0]["reason"] and f"Gate {hit}" in out["lane_changes"][0]["reason"]


def test_the_spike_only_raises_the_queue_of_the_lane_it_hit(svc):
    before = svc.lane_view(DATE, 10)
    svc.reoptimize(queue_spike_pct=200, window_hours=1, start=SLOT10, lane=2, now=NOW)
    after = svc.lane_view(DATE, 10)
    for b, a in zip(before["lanes"], after["lanes"]):
        if b["lane"] == 2:
            assert a["predicted_queue_length"] == pytest.approx(b["predicted_queue_length"] * 3, rel=0.02)
        else:
            assert a["predicted_queue_length"] == b["predicted_queue_length"]
    assert after["disruption"]["lane"] == 2


def test_small_differences_do_not_cause_pointless_gate_changes(svc):
    a = book(svc, 1)
    svc.approve(a["id"])
    out = svc.rebalance_lanes(NOW)
    assert out == [] and [e["event_type"] for e in svc.repo.events(a["id"])] == ["ASSIGNED", "APPROVED"]


def test_rebalancing_never_touches_past_hours(svc):
    a = book(svc, 1)
    svc.close_lane(a["lane"], hours=2, start=SLOT10, now=NOW)  # moved now (the booked hour is upcoming)
    b = book(svc, 2, hour=11)
    svc.closures.clear()
    svc.close_lane(b["lane"], hours=1, start=f"{DATE}T11:00", now=NOW)
    moved_lane = lane_of(svc, b["id"])
    late = datetime(2030, 1, 7, 15, 0)  # both hours are now in the past
    assert svc.rebalance_lanes(late) == [] and lane_of(svc, b["id"]) == moved_lane


# ---- delay notices -----------------------------------------------------------------------------------------

def test_drivers_are_told_when_the_expected_wait_rises(svc):
    a = book(svc, 1)
    svc.approve(a["id"])
    out = svc.reoptimize(vessel_delay_hours=4, queue_spike_pct=100, window_hours=1, start=SLOT10, now=NOW)
    assert out["delay_notices"] >= 1
    notes = [n for n in svc.notifications(a["id"]) if n["type"] == "DELAY_UPDATE"]
    assert len(notes) == 1
    assert "rose from" in notes[0]["message"] and "vessel delay of 4 h" in notes[0]["message"] and "queue spike of +100%" in notes[0]["message"]


def test_the_same_delay_is_not_announced_twice(svc):
    a = book(svc, 1)
    svc.approve(a["id"])  # an approved booking keeps its slot, so it is told rather than moved
    svc.reoptimize(vessel_delay_hours=4, queue_spike_pct=100, window_hours=1, start=SLOT10, now=NOW)
    svc.reoptimize(vessel_delay_hours=4, queue_spike_pct=100, window_hours=1, start=SLOT10, now=NOW)
    assert len([n for n in svc.notifications(a["id"]) if n["type"] == "DELAY_UPDATE"]) == 1


def test_drivers_outside_the_disrupted_hour_hear_nothing(svc):
    a = book(svc, 1, hour=16)
    svc.reoptimize(vessel_delay_hours=4, queue_spike_pct=100, window_hours=1, start=SLOT10, now=NOW)
    assert not [n for n in svc.notifications(a["id"]) if n["type"] == "DELAY_UPDATE"]


# ---- the driver's live view ------------------------------------------------------------------------------------

def test_live_view_follows_the_whole_journey(svc):
    a = book(svc, 1)
    aid = a["id"]
    assert svc.live(aid, NOW)["phase"] == "awaiting_approval" and svc.live(aid, NOW)["live"] is None
    svc.approve(aid)
    approved = svc.live(aid, NOW)
    assert approved["phase"] == "upload_documents" and "Upload your documents" in approved["next_step"]
    svc.repo.update(aid, missing_documents=2)
    assert svc.live(aid, NOW)["phase"] == "fix_documents"
    svc.repo.update(aid, missing_documents=0)
    ready = svc.live(aid, NOW)
    assert ready["phase"] == "ready" and f"Gate {a['lane']}" in ready["next_step"]
    assert svc.live(aid, datetime(2030, 1, 7, 10, 20))["phase"] == "arrive_now"
    assert svc.live(aid, datetime(2030, 1, 7, 12, 0))["phase"] == "past"


def test_live_view_shows_rejected_waitlisted_and_cancelled(svc):
    a, b, c = book(svc, 1), book(svc, 2), book(svc, 3)
    svc.reject(a["id"], "No capacity")
    svc.cancel(b["id"])
    assert svc.live(a["id"], NOW)["phase"] == "rejected" and svc.live(b["id"], NOW)["phase"] == "cancelled"
    assert svc.live(c["id"], NOW)["phase"] == "awaiting_approval"


def test_live_view_reports_the_gate_the_delay_and_the_reason(svc):
    a = book(svc, 1)
    svc.approve(a["id"])
    calm = svc.live(a["id"], NOW)["live"]
    assert calm["delay_min"] == 0 and calm["reasons"] == [] and calm["lane"] == a["lane"]
    assert calm["gate_entry"] < calm["departure"] and calm["monitor"] == {"date": DATE, "hour": 10}
    svc.reoptimize(vessel_delay_hours=4, queue_spike_pct=100, window_hours=1, start=SLOT10, now=NOW)
    live = svc.live(a["id"], NOW)["live"]
    assert live["delay_min"] > 0 and live["expected_wait_min"] > live["normal_wait_min"]
    assert any("vessel delay of 4 h" in r for r in live["reasons"])
    assert live["gate_entry"] > calm["gate_entry"]  # the expected gate entry moves later with the delay


def test_live_view_names_a_delayed_linked_vessel(svc):
    a = book(svc, 1, vessel_delay=True)
    svc.repo.update(a["id"], vessel_name="MV OCEAN PIONEER", vessel_delay_hours=5.0)
    svc.approve(a["id"])
    reasons = svc.live(a["id"], NOW)["live"]["reasons"]
    assert any("MV OCEAN PIONEER" in r and "delayed 5 h" in r for r in reasons)


def test_live_view_follows_a_gate_change(svc):
    a = book(svc, 1)
    svc.approve(a["id"])
    old = a["lane"]
    svc.close_lane(old, hours=2, start=SLOT10, reason="breakdown", now=NOW)
    live = svc.live(a["id"], NOW)
    assert live["live"]["lane"] != old and live["appointment"]["lane"] == live["live"]["lane"]
    assert live["notifications"][0]["type"] == "LANE_CHANGED"


def test_notifications_are_newest_first_with_titles_and_levels(svc):
    a = book(svc, 1)
    svc.approve(a["id"])
    svc.close_lane(a["lane"], hours=1, start=SLOT10, now=NOW)
    notes = svc.notifications(a["id"])
    assert [n["type"] for n in notes] == ["LANE_CHANGED", "APPROVED", "ASSIGNED"]
    assert [n["title"] for n in notes] == ["Gate changed", "Approved by the gate admin", "Request received"]
    assert [n["level"] for n in notes] == ["warning", "success", "info"]


def test_unknown_appointment_is_reported(svc):
    with pytest.raises(BookingError):
        svc.live(999, NOW)
    with pytest.raises(BookingError):
        svc.notifications(999)
