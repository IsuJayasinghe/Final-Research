from datetime import datetime, timedelta

import pytest

import scheduler as sch
from scheduler import BookingState, Disruption

T0 = datetime(2030, 1, 7, 9, 0)  # a Monday 09:00, far in the future
EARLIEST = datetime(2030, 1, 7, 0, 0)


def flat_wait(_slot):
    return 10.0


def fill(slot, n, p_no_show, start_id=1):
    return [BookingState(start_id + i, slot, slot, p_no_show) for i in range(n)]


def test_accepts_requested_slot_when_empty():
    d = sch.decide_slot(T0, 0.05, [], EARLIEST, flat_wait)
    assert d.slot == T0 and not d.overbooked and d.status == "PENDING"


def test_overbooks_when_expected_arrivals_fit_capacity():
    # capacity 6 filled, but each booking is 50% likely to no-show -> expected 3.0
    bookings = fill(T0, 6, 0.5)
    d = sch.decide_slot(T0, 0.5, bookings, EARLIEST, flat_wait, capacity=6, max_overbook=2)
    assert d.slot == T0
    assert d.overbooked
    assert d.expected_after == pytest.approx(3.5)


def test_does_not_overbook_reliable_bookings():
    # six dependable bookings really will all arrive -> a 7th must go elsewhere
    bookings = fill(T0, 6, 0.0)
    d = sch.decide_slot(T0, 0.0, bookings, EARLIEST, flat_wait, capacity=6, max_overbook=2)
    assert d.slot != T0 and not d.overbooked


def test_overbook_cap_is_enforced():
    # expected arrivals are tiny, but bookings may never exceed capacity + MAX_OVERBOOK
    bookings = fill(T0, 8, 0.9)
    d = sch.decide_slot(T0, 0.9, bookings, EARLIEST, flat_wait, capacity=6, max_overbook=2)
    assert d.slot != T0


def test_waitlists_when_everything_nearby_is_full():
    bookings = []
    for h in range(-sch.SEARCH_RADIUS_HOURS, sch.SEARCH_RADIUS_HOURS + 1):
        bookings += fill(T0 + timedelta(hours=h), 8, 0.0, start_id=1000 + (h + 10) * 20)
    d = sch.decide_slot(T0, 0.0, bookings, EARLIEST, flat_wait, capacity=6, max_overbook=2)
    assert d.slot is None and d.status == "WAITLISTED"


def test_prefers_less_congested_neighbour_slot():
    wait = lambda s: 60.0 if s == T0 else 5.0  # noqa: E731
    d = sch.decide_slot(T0, 0.05, [], EARLIEST, wait)
    assert d.slot != T0
    assert abs((d.slot - T0).total_seconds()) == 3600  # moves one hour, not more


def test_never_schedules_before_earliest():
    d = sch.decide_slot(T0, 0.05, [], T0, flat_wait)
    assert d.slot >= T0


def test_reoptimize_moves_unconfirmed_away_from_disrupted_window_only():
    base = lambda s: 30.0  # noqa: E731  (realistic ~30 min expected wait)
    dis = Disruption(kind="vessel_delay", vessel_delay_hours=4, start=T0, window_hours=1)
    wait = lambda s: base(s) * (1 + dis.uplift(s))  # noqa: E731
    unconfirmed = fill(T0, 3, 0.1)
    confirmed = [BookingState(99, T0, T0, 0.1, status="CONFIRMED")]
    moves = sch.reoptimize(unconfirmed, confirmed, EARLIEST, wait)
    assert all(m.new_slot != T0 for m in moves)  # +60% congestion (+18 min) outweighs move penalties
    assert len(moves) == 3
    assert confirmed[0].assigned_slot == T0  # confirmed bookings are untouched


def test_reoptimize_respects_expected_capacity():
    unconfirmed = fill(T0, 12, 0.0)  # dependable bookings, capacity 6 per slot
    moves = sch.reoptimize(unconfirmed, [], EARLIEST, flat_wait, capacity=6, max_overbook=0)
    per_slot = {}
    for m in moves:
        per_slot[m.new_slot] = per_slot.get(m.new_slot, 0) + 1
    assert max(per_slot.values()) <= 6


def test_small_disruption_does_not_cause_pointless_moves():
    # +6 min of extra wait is cheaper than the 10 min cost of moving -> stay put
    dis = Disruption(kind="vessel_delay", vessel_delay_hours=4, start=T0, window_hours=1)
    wait = lambda s: 10.0 * (1 + dis.uplift(s))  # noqa: E731
    moves = sch.reoptimize(fill(T0, 3, 0.1), [], EARLIEST, wait)
    assert all(m.new_slot == T0 for m in moves)


def test_reoptimize_leaves_everything_when_nothing_changed():
    unconfirmed = fill(T0, 3, 0.1)
    moves = sch.reoptimize(unconfirmed, [], EARLIEST, flat_wait)
    assert all(m.new_slot == m.old_slot for m in moves)


def test_explain_move_cites_congestion_percentage():
    dis = Disruption(kind="vessel_delay", vessel_delay_hours=2, start=T0, window_hours=2)
    base = lambda s: 10.0  # noqa: E731
    wait = lambda s: 10.0 * (1 + dis.uplift(s))  # noqa: E731
    move = sch.Move(1, T0, T0 + timedelta(hours=2), 16.0, 12.0)
    reasons = sch.explain_move(move, base, wait, dis, risk_summary="No-show risk 12%.")
    assert "30%" in reasons[0] and "vessel delay of 2h" in reasons[0]
    assert any("Moved to" in r for r in reasons)
    assert reasons[-1] == "No-show risk 12%."
