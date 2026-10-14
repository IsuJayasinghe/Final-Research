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


# ---- unknown document facts ---------------------------------------------------------------

def args(**kw):
    base = dict(
        arrival=ARRIVAL,
        carrier="Carrier-B",
        container_type="hazardous",
        cargo_category="export",
        carrier_reliability=0.54,
        lead_time_hours=34,
        weather_severity=1,
    )
    base.update(kw)
    return base


def test_known_documents_match_the_plain_prediction():
    out = noshow.predict_risk_for_documents("low", 0, **args())
    plain = noshow.predict_risk(noshow.build_row(customs_risk_flag="low", missing_documents=0, **args()))
    assert out["p_no_show"] == plain["p_no_show"] and out["documents_known"] is True


def test_unknown_documents_fall_between_the_best_and_worst_case():
    unknown = noshow.predict_risk_for_documents(None, None, **args())
    best = noshow.predict_risk_for_documents("low", 0, **args())["p_no_show"]
    worst = noshow.predict_risk_for_documents("high", 3, **args())["p_no_show"]
    assert best < unknown["p_no_show"] < worst
    assert unknown["documents_known"] is False and "not checked yet" in unknown["summary"]
    assert abs(unknown["p_on_time"] + unknown["p_late"] + unknown["p_no_show"] - 1) < 1e-3


def test_unknown_documents_are_not_presented_as_drivers():
    out = noshow.predict_risk_for_documents(None, None, **args())
    labels = " ".join(d["label"] for d in out["drivers"])
    assert "missing document" not in labels and "customs" not in labels and len(out["drivers"]) == 3


def test_partially_known_documents_narrow_the_estimate():
    both_unknown = noshow.predict_risk_for_documents(None, None, **args())["p_no_show"]
    high_customs = noshow.predict_risk_for_documents("high", None, **args())["p_no_show"]
    low_customs = noshow.predict_risk_for_documents("low", None, **args())["p_no_show"]
    assert low_customs < both_unknown < high_customs


def test_document_scenarios_cover_the_prior():
    scen = noshow.document_scenarios(None, None)
    assert len(scen) == 12 and abs(sum(w for *_, w in scen) - 1) < 1e-9
    assert noshow.document_scenarios("low", 9) == [("low", 3, 1.0)]  # missing count is capped at the trained range


# ---- unknown weather and vessel delay, carrier profiles ----------------------------------------------

def test_unknown_weather_falls_between_clear_and_storm():
    clear = noshow.predict_risk_for_documents("low", 0, **args(weather_severity=0))["p_no_show"]
    storm = noshow.predict_risk_for_documents("low", 0, **args(weather_severity=3))["p_no_show"]
    unknown = noshow.predict_risk_for_documents("low", 0, **args(weather_severity=None))
    assert clear < unknown["p_no_show"] < storm
    assert unknown["weather_known"] is False and "weather forecast unavailable" in unknown["summary"].lower()
    assert not any(d["feature"] == "weather_severity" for d in unknown["drivers"])


def test_unknown_vessel_delay_falls_between_on_time_and_delayed():
    on_time = noshow.predict_risk_for_documents("low", 0, **args(vessel_delay=False))["p_no_show"]
    delayed = noshow.predict_risk_for_documents("low", 0, **args(vessel_delay=True))["p_no_show"]
    unknown = noshow.predict_risk_for_documents("low", 0, **args(vessel_delay=None))
    assert on_time < unknown["p_no_show"] < delayed
    assert unknown["vessel_known"] is False and "vessel delay not known yet" in unknown["summary"].lower()


def test_everything_unknown_is_still_a_valid_distribution_and_names_each_gap():
    out = noshow.predict_risk_for_documents(None, None, **args(weather_severity=None, vessel_delay=None))
    assert abs(out["p_on_time"] + out["p_late"] + out["p_no_show"] - 1) < 1e-3
    assert "documents not checked yet" in out["summary"].lower()
    assert "vessel delay not known yet" in out["summary"] and "weather forecast unavailable" in out["summary"]
    assert not any(out[k] for k in ("documents_known", "weather_known", "vessel_known"))


def test_weather_prior_is_seasonal():
    monsoon = noshow.weather_scenarios(None, 11)
    dry = noshow.weather_scenarios(None, 2)
    assert dict(monsoon)[0] < dict(dry)[0]  # clear days are rarer in the monsoon
    assert abs(sum(w for _, w in monsoon) - 1) < 1e-9 and noshow.weather_scenarios(2, 11) == [(2, 1.0)]


def test_carrier_profiles_come_from_the_model():
    b = noshow.carrier_profile("Carrier-B")
    assert 0.45 < b["reliability"] < 0.6 and b["past_no_show_rate"] > 0.15  # the unreliable carrier
    j = noshow.carrier_profile("Carrier-J")
    assert j["reliability"] > 0.8 and j["past_no_show_rate"] < 0.06
    assert noshow.carrier_profile("Carrier-ZZZ") is None
    assert [p["carrier"] for p in noshow.carrier_profiles()][:2] == ["Carrier-A", "Carrier-B"]
