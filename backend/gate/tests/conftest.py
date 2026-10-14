import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    """Tests never call a real external API: the forecast is unreachable unless a test supplies its own."""
    import urllib.error

    import weather

    def offline(*args, **kwargs):
        raise urllib.error.URLError("network disabled in tests")

    monkeypatch.setattr(weather.urllib.request, "urlopen", offline)
    monkeypatch.setattr(weather.time, "sleep", lambda s: None)
    weather.clear_cache()
    yield
    weather.clear_cache()
