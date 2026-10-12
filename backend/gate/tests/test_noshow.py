from datetime import datetime

import pytest

import noshow

ARRIVAL = datetime(2030, 1, 7, 9, 0)


@pytest.fixture(scope="module", autouse=True)
def _model():
    noshow.load_model()


def row(**kw):
    base = dict(
        arrival=ARRIVAL,
        carrier="Carrier-A",
        container_type="standard",
        cargo_category="import",
        customs_risk_flag="low",
        missing_documents=0,
        carrier_reliability=0.8,
        lead_time_hours=24,
    )
    base.update(kw)
    return noshow.build_row(**base)


def test_probabilities_sum_to_one():
    out = noshow.predict_risk(row())
    assert out["p_on_time"] + out["p_late"] + out["p_no_show"] == pytest.approx(1.0, abs=1e-3)


def test_risky_booking_scores_much_higher_than_safe_one():
    safe = noshow.predict_risk(row(carrier="Carrier-J", carrier_reliability=0.87, lead_time_hours=6))
    risky = noshow.predict_risk(
        row(carrier="Carrier-B", carrier_reliability=0.54, missing_documents=3, lead_time_hours=90, vessel_delay=True)
    )
    assert risky["p_no_show"] > safe["p_no_show"] * 5


def test_more_missing_documents_never_lowers_risk():
    risks = [noshow.predict_risk(row(missing_documents=m))["p_no_show"] for m in (0, 1, 3)]
    assert risks[0] < risks[2]


def test_explanation_lists_top_drivers_with_direction():
    out = noshow.predict_risk(row(carrier="Carrier-B", carrier_reliability=0.54, missing_documents=3))
    assert len(out["drivers"]) == 3
    assert all(d["effect"] in ("raises", "lowers") for d in out["drivers"])
    assert out["summary"].startswith("No-show risk")
    assert any("missing document" in d["label"] or "reliability" in d["label"] for d in out["drivers"])


def test_unknown_carrier_falls_back_to_defaults():
    out = noshow.predict_risk(row(carrier="Carrier-ZZZ"))
    assert 0 <= out["p_no_show"] <= 1
