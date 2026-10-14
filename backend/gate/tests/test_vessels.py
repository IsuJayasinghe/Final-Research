import pytest

import vessels

DAY = "2030-01-09"


@pytest.fixture(autouse=True)
def _no_external_api(monkeypatch):
    monkeypatch.delenv("VESSEL_API_URL", raising=False)


def test_name_is_normalised():
    assert vessels.normalise_vessel("  mv  ever   grace ") == "MV EVER GRACE"
    assert vessels.normalise_vessel(None) == ""


def test_named_demo_vessels_have_fixed_delays():
    ok = vessels.get_vessel_delay("MV Ever Grace", DAY)
    late = vessels.get_vessel_delay("mv ocean pioneer", DAY)
    assert ok["delay_hours"] == 0 and ok["delayed"] is False
    assert late["delay_hours"] == 5 and late["delayed"] is True
    assert "simulated" in late["source"]


def test_unknown_vessels_are_deterministic_and_about_twelve_percent_delayed():
    first = vessels.get_vessel_delay("MV TEST ONE", DAY)
    assert first == vessels.get_vessel_delay("MV TEST ONE", DAY)  # same vessel and day -> same answer
    delayed = [vessels.get_vessel_delay(f"MV SHIP {i}", DAY)["delayed"] for i in range(400)]
    assert 0.06 < sum(delayed) / len(delayed) < 0.18
    hours = [vessels.get_vessel_delay(f"MV SHIP {i}", DAY)["delay_hours"] for i in range(400)]
    assert max(hours) <= 10 and all(h == 0 or h >= 2 for h in hours)


def test_no_vessel_means_unknown():
    out = vessels.get_vessel_delay(None, DAY)
    assert out["delayed"] is None and out["delay_hours"] is None


def test_delay_threshold_decides_delayed():
    assert vessels.get_vessel_delay("MV X", DAY, fetch=lambda v, d: 1.5)["delayed"] is False
    out = vessels.get_vessel_delay("MV X", DAY, fetch=lambda v, d: 2.0)
    assert out["delayed"] is True and out["source"] == "vessel-api"


def test_failed_api_gives_unknown_never_a_guess():
    out = vessels.get_vessel_delay("MV X", DAY, fetch=lambda v, d: None)
    assert out["delayed"] is None and out["delay_hours"] is None and out["source"] == "unavailable"


def test_configured_api_url_replaces_the_simulation(monkeypatch):
    monkeypatch.setenv("VESSEL_API_URL", "http://127.0.0.1:9/never-listening")
    out = vessels.get_vessel_delay("MV OCEAN PIONEER", DAY)  # a demo vessel, but the real feed is configured and down
    assert out["delayed"] is None and out["source"] == "unavailable"
