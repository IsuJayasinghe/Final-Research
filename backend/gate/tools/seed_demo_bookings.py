"""
Fill the gate with realistic DEMO bookings through the public API, so the slot board, the lane monitor and the
optimizer have something to show when there is no real booking data.

The bookings follow the real hourly demand profile (busy mornings and afternoons, quiet nights), use the ten carriers,
valid ISO 6346 container numbers and the same container-type mix as the training data. Each one goes through
POST /api/appointments exactly like a driver's booking, so the no-show risk, overbooking rule and lane allocation all
apply. Roughly 40% are then confirmed; the rest stay PENDING (and can be re-optimized after a disruption).

Everything is demo data created in the running backend (in memory unless you set a DATABASE_URL): restart the backend to
clear it. Truck IDs start TRK-9 so demo trucks are easy to tell apart from yours.

Usage:
    python tools/seed_demo_bookings.py                      # 60 bookings for tomorrow
    python tools/seed_demo_bookings.py --date 2026-10-16 --count 120
    python tools/seed_demo_bookings.py --url http://127.0.0.1:8000 --seed 7
"""

import argparse
import json
import random
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from documents import iso6346_check_digit  # noqa: E402

# Hourly demand profile of the congestion dataset (mean trucks arriving per lane-hour).
HOURLY_DEMAND = [3.9, 3.9, 3.9, 3.8, 3.9, 4.8, 6.5, 8.3, 10.1, 10.8, 11.0, 10.1,
                 9.2, 10.0, 11.0, 10.9, 10.1, 9.2, 7.5, 6.5, 5.7, 4.8, 4.8, 3.9]
CARRIERS = [f"Carrier-{c}" for c in "ABCDEFGHIJ"]
CONTAINER_TYPES = (["standard", "reefer", "hazardous", "oversized"], [0.55, 0.20, 0.10, 0.15])
OWNER_CODES = ["MAEU", "OOLU", "TCLU", "CMAU", "MSKU", "HLCU"]
CONFIRM_PATTERN = (0, 2)  # of every 5 bookings, these positions are confirmed (40%); the rest stay PENDING


def container_number(rng: random.Random) -> str:
    code = rng.choice(OWNER_CODES) + f"{rng.randrange(0, 1_000_000):06d}"
    return code + str(iso6346_check_digit(code))


def should_confirm(index: int) -> bool:
    return index % 5 in CONFIRM_PATTERN


def build_bookings(day: str, count: int, seed: int = 42, risky_share: float = 0.15) -> list[dict]:
    """`count` demo booking requests for `day`, following the hourly demand profile (deterministic for a seed).

    `risky_share` of them come from Carrier-B, the least reliable carrier (about 21% past no-shows), whose bookings are
    the ones the overbooking rule can safely double up."""
    rng = random.Random(seed)
    hours = rng.choices(range(24), weights=HOURLY_DEMAND, k=count)
    types = rng.choices(CONTAINER_TYPES[0], weights=CONTAINER_TYPES[1], k=count)
    bookings = []
    for i, (hour, ctype) in enumerate(zip(sorted(hours), types)):
        bookings.append(
            {
                "truck_id": f"TRK-9{i:04d}",
                "container_id": container_number(rng),
                "carrier": "Carrier-B" if rng.random() < risky_share else rng.choice([c for c in CARRIERS if c != "Carrier-B"]),
                "cargo_category": rng.choice(["export", "import"]),
                "container_type": ctype,
                "arrival_date": day,
                "arrival_hour": hour,
            }
        )
    return bookings


def _call(url: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--date", default=(date.today() + timedelta(days=1)).isoformat(), help="arrival date (default: tomorrow)")
    parser.add_argument("--count", type=int, default=60, help="number of bookings (default 60)")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="backend base URL (127.0.0.1 is much faster than localhost on Windows)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--risky-share", type=float, default=0.15, help="share of bookings from the unreliable Carrier-B (default 0.15)")
    args = parser.parse_args()

    try:
        health = _call(args.url + "/")
    except (urllib.error.URLError, OSError):
        print(f"Cannot reach the backend at {args.url}. Start it first (python -m uvicorn main:app --port 8000).")
        return 1
    print(f"Backend OK (storage: {health.get('storage')}). Creating {args.count} demo bookings for {args.date} ...")

    created, overbooked, waitlisted, confirmed = [], 0, 0, 0
    for i, booking in enumerate(build_bookings(args.date, args.count, args.seed, args.risky_share)):
        try:
            out = _call(args.url + "/api/appointments", "POST", booking)
        except urllib.error.HTTPError as e:
            print(f"  booking {booking['truck_id']} rejected: {e.read().decode()[:120]}")
            continue
        appt = out["appointment"]
        created.append(appt)
        overbooked += bool(appt["overbooked"])
        waitlisted += appt["status"] == "WAITLISTED"
        if appt["status"] == "PENDING" and should_confirm(i):
            _call(f"{args.url}/api/appointments/{appt['id']}/confirm", "POST", {})
            confirmed += 1

    per_hour: dict[int, int] = {}
    for a in created:  # only the target day: bookings near midnight can spill into the neighbouring day
        if a["assigned_slot"] and a["assigned_slot"].startswith(args.date):
            per_hour[int(a["assigned_slot"][11:13])] = per_hour.get(int(a["assigned_slot"][11:13]), 0) + 1
    print(f"Created {len(created)} bookings: {confirmed} confirmed, {overbooked} overbooked, {waitlisted} waitlisted.")
    print("Bookings per hour: " + "  ".join(f"{h:02d}h:{n}" for h, n in sorted(per_hour.items())))
    print(f"Now open the Gate Allocation page and pick {args.date}; the busiest hour is the peak of the list above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
