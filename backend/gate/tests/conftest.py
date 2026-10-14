import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_real_network_for_weather(monkeypatch):
    """Tests never call the real weather API; an unreachable forecast must be handled gracefully."""
    import weather

    monkeypatch.setattr(weather, "_fetch_open_meteo", lambda day: None)
    weather.clear_cache()
    yield
    weather.clear_cache()
