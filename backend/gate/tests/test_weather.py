from datetime import date, timedelta

import pytest

import weather

TODAY = date(2030, 1, 7)
DAY = "2030-01-09"


@pytest.fixture(autouse=True)
def _fresh_cache():
    weather.clear_cache()
    yield
    weather.clear_cache()


@pytest.mark.parametrize(
    "code,rain,wind,expected",
    [
        (0, 0.0, 10, 0),       # clear
        (3, 0.4, 15, 0),       # overcast, trace rain
        (61, 3.0, 20, 1),      # light rain
        (51, 0.0, 10, 1),      # drizzle code
        (81, 13.1, 12.2, 2),   # the real Colombo forecast seen while building this: heavy rain showers
        (65, 5.0, 10, 2),      # heavy-rain weather code
        (63, 35.0, 30, 3),     # extreme rainfall
        (95, 8.0, 20, 3),      # thunderstorm
        (1, 0.0, 70, 3),       # damaging wind
        (None, None, None, 0),
    ],
)
def test_severity_scale(code, rain, wind, expected):
    assert weather.severity_from_forecast(code, rain, wind) == expected


def fake(**kw):
    raw = {"weather_code": 81, "precipitation_mm": 13.1, "wind_kmh": 12.2}
    raw.update(kw)
    return lambda day: raw


def test_forecast_is_mapped_to_severity_and_labelled():
    out = weather.get_weather(DAY, fetch=fake(), today=TODAY)
    assert out["severity"] == 2 and out["label"] == "Heavy rain" and out["source"] == "open-meteo"
    assert out["precipitation_mm"] == 13.1


def test_result_is_cached_so_the_api_is_called_once():
    calls = []

    def counting(day):
        calls.append(day)
        return {"weather_code": 0, "precipitation_mm": 0, "wind_kmh": 5}

    weather.get_weather(DAY, fetch=counting, today=TODAY)
    weather.get_weather(DAY, fetch=counting, today=TODAY)
    assert calls == [DAY]


def test_unavailable_forecast_is_unknown_not_guessed():
    out = weather.get_weather(DAY, fetch=lambda d: None, today=TODAY)
    assert out["severity"] is None and out["label"] is None and out["source"] == "unavailable"


def test_failures_are_remembered_briefly():
    calls = []

    def failing(day):
        calls.append(day)
        return None

    weather.get_weather(DAY, fetch=failing, today=TODAY)
    weather.get_weather(DAY, fetch=failing, today=TODAY)
    assert len(calls) == 1  # an offline machine does not wait on the network for every request


def test_dates_outside_the_forecast_range_are_unknown_without_calling_the_api():
    def boom(day):
        raise AssertionError("must not call the API")

    far = (TODAY + timedelta(days=weather.FORECAST_DAYS)).isoformat()
    assert weather.get_weather(far, fetch=boom, today=TODAY)["source"] == "beyond-forecast-range"
    assert weather.get_weather("2029-12-31", fetch=boom, today=TODAY)["source"] == "past-date"
    assert weather.get_weather("not-a-date", fetch=boom, today=TODAY)["source"] == "invalid-date"
    last_ok = (TODAY + timedelta(days=weather.FORECAST_DAYS - 1)).isoformat()
    assert weather.get_weather(last_ok, fetch=fake(), today=TODAY)["severity"] == 2
