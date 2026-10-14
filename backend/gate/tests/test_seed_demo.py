from collections import Counter

import documents
from tools import seed_demo_bookings as seed


def test_builds_the_requested_number_of_valid_demo_bookings():
    bookings = seed.build_bookings("2031-03-12", 80)
    assert len(bookings) == 80
    assert len({b["truck_id"] for b in bookings}) == 80 and all(b["truck_id"].startswith("TRK-9") for b in bookings)
    assert all(documents.valid_container_number(b["container_id"]) for b in bookings)
    assert all(b["carrier"].startswith("Carrier-") and b["arrival_date"] == "2031-03-12" for b in bookings)
    # a driver only enters who/what/when: nothing else is supplied
    assert set(bookings[0]) == {"truck_id", "container_id", "carrier", "cargo_category", "container_type", "arrival_date", "arrival_hour"}


def test_demo_is_deterministic_and_the_seed_changes_it():
    assert seed.build_bookings("2031-03-12", 30, seed=1) == seed.build_bookings("2031-03-12", 30, seed=1)
    assert seed.build_bookings("2031-03-12", 30, seed=1) != seed.build_bookings("2031-03-12", 30, seed=2)


def test_arrivals_follow_the_real_demand_profile():
    hours = Counter(b["arrival_hour"] for b in seed.build_bookings("2031-03-12", 2000))
    quiet = sum(hours[h] for h in (0, 1, 2, 3, 4))
    busy = sum(hours[h] for h in (9, 10, 14, 15))
    assert busy > quiet * 1.5
    assert all(0 <= h <= 23 for h in hours)


def test_container_type_mix_matches_the_training_data():
    types = Counter(b["container_type"] for b in seed.build_bookings("2031-03-12", 2000))
    assert 0.45 < types["standard"] / 2000 < 0.65 and types["hazardous"] / 2000 < 0.15
