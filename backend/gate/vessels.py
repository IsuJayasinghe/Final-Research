"""
Linked-vessel delay for a booking.

The technical plan takes vessel ETA / delay data from the vessel ETA and berth allocation component
(Component 1). That component is not connected yet, so this module is the single connection point:

  * VESSEL_API_URL set  -> GET {url}?vessel=<name>&date=<YYYY-MM-DD>, expecting JSON {"delay_hours": <number>}
                           (the contract Component 1 would expose); failures give "unknown", never a guess.
  * otherwise           -> a clearly labelled SIMULATED schedule: a few named demo vessels with fixed delays, and
                           a deterministic ~12% delayed rate for any other vessel (matches the training data).

The vessel itself is not typed in: its name is read from the booking confirmation with OCR.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

DELAY_THRESHOLD_H = 2.0  # "linked vessel delayed" in the training data means a delay of at least this long
SIMULATED_DELAY_RATE = 0.12
SIMULATED_SOURCE = "simulated schedule (Component 1 feed not connected)"
TIMEOUT_S = 5

# Named demo vessels, so a demo can show an on-time and delayed vessel on purpose.
DEMO_SCHEDULE = {
    "MV EVER GRACE": 0.0,
    "MV LANKA EXPRESS": 0.0,
    "MV OCEAN PIONEER": 5.0,
    "MV PACIFIC STAR": 3.0,
    "MAERSK COLOMBO": 0.0,
}


def _compact(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", re.sub(r"^(?:MV|M/V|MS)\b\.?\s*", "", name.upper()))


def normalise_vessel(name: str | None) -> str:
    """Upper-case, single spaces; a name the OCR read without spaces ("MAERSKCOLOMBO") is restored to the known name."""
    cleaned = re.sub(r"\s+", " ", (name or "").upper()).strip()
    for known in DEMO_SCHEDULE:
        if cleaned and _compact(cleaned) == _compact(known):
            return known
    return cleaned


def _simulated(vessel: str, day: str) -> float:
    if vessel in DEMO_SCHEDULE:
        return DEMO_SCHEDULE[vessel]
    h = int(hashlib.sha256(f"{vessel}|{day}".encode()).hexdigest()[:8], 16)
    if h % 100 < SIMULATED_DELAY_RATE * 100:
        return float(2 + (h // 100) % 9)  # 2-10 hours
    return 0.0


def _fetch_api(base_url: str, vessel: str, day: str) -> float | None:
    query = urllib.parse.urlencode({"vessel": vessel, "date": day})
    try:
        with urllib.request.urlopen(f"{base_url}?{query}", timeout=TIMEOUT_S) as resp:
            value = json.load(resp)["delay_hours"]
        return float(value)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, TypeError, OSError):
        return None


def get_vessel_delay(vessel_name: str | None, day: str, fetch: Callable[[str, str], float | None] | None = None) -> dict:
    """{"vessel", "delay_hours", "delayed", "source"}; delayed/delay_hours are None when unknown."""
    vessel = normalise_vessel(vessel_name)
    if not vessel:
        return {"vessel": None, "delay_hours": None, "delayed": None, "source": "no-vessel"}

    api_url = os.environ.get("VESSEL_API_URL")
    if fetch is not None or api_url:
        hours = (fetch or (lambda v, d: _fetch_api(api_url, v, d)))(vessel, day)
        if hours is None:
            return {"vessel": vessel, "delay_hours": None, "delayed": None, "source": "unavailable"}
        return {"vessel": vessel, "delay_hours": hours, "delayed": hours >= DELAY_THRESHOLD_H, "source": "vessel-api"}

    hours = _simulated(vessel, day)
    return {"vessel": vessel, "delay_hours": hours, "delayed": hours >= DELAY_THRESHOLD_H, "source": SIMULATED_SOURCE}
