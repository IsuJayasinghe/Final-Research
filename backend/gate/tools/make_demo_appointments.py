"""
Create three different demo appointments for the OCR document-check demo, each with its own set of made-up documents.

  1  clean      standard container, ordinary goods, vessel on time      -> everything clears, low customs risk
  2  hazardous  dangerous goods, fuel cargo, vessel delayed 5 h         -> a wrong-container VGM and an expired
                                                                          gate pass are flagged, then fixed
  3  reefer     chilled wine (high-scrutiny goods), vessel delayed 3 h  -> a missing seal number, incomplete driver
                                                                          documents and a blurry gate pass are
                                                                          flagged, then fixed

The documents are drawn in the layout of the real forms (grids, tables, a ticked check box, a numbered driving licence
card; see real_format_documents.py). Every scenario folder holds the documents to upload under their slot names
(vgm.png, gate_pass.png, ...). Faulty versions are named <slot>__PROBLEM_<what>.png: upload those first to see the
checks fail, then replace them with the file of the same slot name. Each folder also has a README.txt with the booking
to make and what to expect.

Usage:
  python tools/make_demo_appointments.py [--out DIR] [--date YYYY-MM-DD]                          write the documents
  python tools/make_demo_appointments.py --book [--approve] [--url http://127.0.0.1:8000]       also book (and approve)

Default output: backend/gate/sample_documents/appointments/ (git-ignored). All contents are made up.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from documents import iso6346_check_digit  # noqa: E402
from tools import real_format_documents as real  # noqa: E402


def container_number(prefix_and_serial: str) -> str:
    """Owner code + serial number + the ISO 6346 check digit, e.g. 'MSCU538204' -> 'MSCU5382042'."""
    return prefix_and_serial + str(iso6346_check_digit(prefix_and_serial))


@dataclass
class Scenario:
    key: str
    title: str
    truck: str
    container: str
    carrier: str
    container_type: str
    cargo_category: str
    hour: int
    vessel: str
    voyage: str
    booking_no: str
    goods: str
    hs: str
    seal: str
    driver_given: str
    driver_surname: str
    licence: str
    plate: str
    weight_kg: str
    shipper: str = "LANKA EXPORTS (PVT) LTD"
    consignee: str = "PACIFIC IMPORTS PTE LTD"
    pod: str = "Singapore (SGP)"
    pod_address: str = "Singapore 079903"
    pod_country: str = "SINGAPORE"
    tare_kg: int = 3900
    vehicle_make: str = "TATA"
    vehicle_model: str = "LPT 1618"
    vehicle_type: str = "LORRY"
    cargo_note: list[str] = field(default_factory=list)  # lines of the special cargo document
    problems: list[tuple[str, str]] = field(default_factory=list)  # (slot, what the faulty file shows)
    expect: list[str] = field(default_factory=list)

    @property
    def owner(self) -> str:
        return self.driver_initials().upper()

    def driver_initials(self) -> str:
        return "".join(f"{w[0]}." for w in self.driver_given.split()) + self.driver_surname.title()


SCENARIOS = [
    Scenario(
        key="1_clean", title="Clean standard export", truck="TRK-81001", container=container_number("MSCU538204"),
        carrier="Carrier-A", container_type="standard", cargo_category="export", hour=8,
        vessel="MV EVER GRACE", voyage="051E", booking_no="OPLBK2610101", goods="Cotton T-shirts", hs="6109.10",
        seal="SL551902", driver_given="KASUN CHAMARA", driver_surname="SILVA", licence="B7654321", plate="WP KA-5521",
        weight_kg="18,900", shipper="LANKA TEXTILES EXPORT (PVT) LTD", consignee="NORDIC FASHION AB",
        pod="Gothenburg (SEGOT)", pod_address="Gothenburg 411 04", pod_country="SWEDEN",
        vehicle_make="ISUZU", vehicle_model="NPR 75",
        expect=[
            "all 6 required documents are cleared",
            "customs risk: low (HS 6109.10, ordinary goods)",
            "vessel MV EVER GRACE is on schedule: no vessel delay",
            "no-show risk goes DOWN after submit; clearance time is shortest of the three",
        ],
    ),
    Scenario(
        key="2_hazardous", title="Hazardous fuel import, delayed vessel", truck="TRK-81002",
        container=container_number("HLCU274519"), carrier="Carrier-B", container_type="hazardous",
        cargo_category="import", hour=10, vessel="MV OCEAN PIONEER", voyage="17W", booking_no="OPLBK2610202",
        goods="Petroleum oils", hs="2710.19", seal="SL662871", driver_given="RUWAN PRASANNA", driver_surname="SILVA",
        licence="B2468013", plate="WP CAC-7810", weight_kg="24,350", shipper="CEYLON PETROCHEM TRADING (PVT) LTD",
        consignee="GULF ENERGY SUPPLIES FZE", pod="Fujairah (AEFJR)", pod_address="Fujairah, UAE",
        pod_country="UNITED ARAB EMIRATES",
        cargo_note=[
            "IMDG Class 3 - Flammable liquid", "UN Number: UN 1203   Packing Group II",
            "Hazard label displayed on all four sides",
        ],
        problems=[("vgm", "wrong_container"), ("gate_pass", "expired")],
        expect=[
            "needs 7 documents (hazardous cargo adds the dangerous goods declaration)",
            "vgm__PROBLEM_wrong_container: flagged, the container number does not match the booking",
            "gate_pass__PROBLEM_expired: flagged, the permit is not valid on the appointment date",
            "after replacing both: 7 of 7 cleared",
            "customs risk: medium (HS 2710.19, mineral fuels)",
            "vessel MV OCEAN PIONEER is delayed 5 h: raises the no-show risk (Carrier-B is also the least reliable carrier)",
        ],
    ),
    Scenario(
        key="3_reefer", title="Reefer wine export, high customs scrutiny", truck="TRK-81003",
        container=container_number("OOLU619842"), carrier="Carrier-C", container_type="reefer",
        cargo_category="export", hour=13, vessel="MV PACIFIC STAR", voyage="233N", booking_no="OPLBK2610303",
        goods="Wine in bottles", hs="2204.21", seal="SL990344", driver_given="MALITH DILSHAN",
        driver_surname="JAYAWARDENA", licence="B1357924", plate="WP CBB-3392", weight_kg="21,480",
        shipper="HILL COUNTRY WINES (PVT) LTD", consignee="ASIA BEVERAGE TRADING PTE LTD", tare_kg=4600,
        vehicle_make="HINO", vehicle_model="FD 8J",
        cargo_note=["Refrigerated container - Set Point: +12 C", "Temperature recorder calibrated"],
        problems=[("seal_match", "no_seal_number"), ("driver_docs", "incomplete"), ("gate_pass", "blurry")],
        expect=[
            "needs 7 documents (the reefer certificate is the special cargo document)",
            "seal_photo__PROBLEM_no_seal_number: flagged, a required detail (seal number) is missing",
            "driver_docs__PROBLEM_incomplete: flagged, no licence number and no vehicle registration",
            "gate_pass__PROBLEM_blurry: flagged, too blurry to be recognised as a gate pass (the system does not guess)",
            "after replacing all three: 7 of 7 cleared",
            "customs risk: high (HS 2204.21, alcohol is high-scrutiny goods)",
            "vessel MV PACIFIC STAR is delayed 3 h",
        ],
    ),
]

# upload slot -> file name (the slot names the document page uses)
SLOT_FILES = {
    "booking_confirmation": "booking_confirmation", "cusdec": "cusdec", "gate_pass": "gate_pass", "vgm": "vgm",
    "seal_match": "seal_photo", "driver_docs": "driver_docs", "special_cargo": "special_cargo",
}


def write_documents(s: Scenario, out: Path, appt_date: str) -> None:
    """The documents in the layout of the real forms, the faulty versions, and a README.txt for the scenario."""
    out.mkdir(parents=True, exist_ok=True)
    real.booking_confirmation(s, out, "booking_confirmation", appt_date)
    real.cusdec(s, out, "cusdec", appt_date)
    real.gate_pass(s, out, "gate_pass", appt_date)
    real.vgm(s, out, "vgm", appt_date)
    real.seal_report(s, out, "seal_photo", appt_date)
    real.driver_card(s, out, "driver_docs", appt_date)
    if s.container_type in ("hazardous", "reefer"):
        real.special_cargo(s, out, "special_cargo", appt_date)

    for slot, what in s.problems:
        name = f"{SLOT_FILES[slot]}__PROBLEM_{what}"
        if slot == "vgm":
            real.vgm(s, out, name, appt_date, container=real.OTHER_CONTAINER)
        elif slot == "gate_pass" and what == "expired":
            real.gate_pass(s, out, name, appt_date, pass_dates=("2019-12-30", "2020-01-01"))
        elif slot == "gate_pass" and what == "blurry":
            real.gate_pass(s, out, "_tmp", appt_date)
            real.blur(out / "_tmp.png", out / f"{name}.png")
            (out / "_tmp.png").unlink()
        elif slot == "seal_match":
            real.seal_report(s, out, name, appt_date, with_seal=False)
        elif slot == "driver_docs":
            real.driver_card(s, out, name, appt_date, complete=False)

    required = 7 if s.container_type in ("reefer", "hazardous") else 6
    lines = [
        f"APPOINTMENT {s.key}: {s.title}",
        "",
        "Book this (Request Appointment page), or run:  python tools/make_demo_appointments.py --book --approve",
        f"  Truck ID        {s.truck}",
        f"  Container ID    {s.container}",
        f"  Carrier         {s.carrier}",
        f"  Container type  {s.container_type}",
        f"  Cargo category  {s.cargo_category}",
        f"  Date / hour     {appt_date}, {s.hour:02d}:00   (documents are dated for this date)",
        "",
        f"Then, as gate admin, approve it. As the driver open Upload Documents ({required} documents are required).",
    ]
    if s.problems:
        lines += ["", "Upload the PROBLEM files first, then replace each with the file of the same slot name:"]
        lines += [f"  {SLOT_FILES[slot]}__PROBLEM_{what}.png  ->  {SLOT_FILES[slot]}.png" for slot, what in s.problems]
    lines += ["", "What you should see:"] + [f"  - {e}" for e in s.expect]
    (out / "README.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def call(url: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url + path, data=data, method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def book(s: Scenario, appt_date: str, url: str, approve: bool) -> None:
    try:
        out = call(url, "/api/appointments", {
            "truck_id": s.truck, "container_id": s.container, "carrier": s.carrier,
            "container_type": s.container_type, "cargo_category": s.cargo_category,
            "arrival_date": appt_date, "arrival_hour": s.hour,
        })
        a = out["appointment"]
        status = a["status"]
        if approve and status == "PENDING":
            status = call(url, f"/api/appointments/{a['id']}/approve", {})["status"]
        print(f"  #{a['id']} {s.truck} {s.container_type:<9} Gate {a['lane']} at {a['assigned_slot'][11:16]}  {status}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Could not reach the backend at {url}: {e}. Start it first (uvicorn main:app --port 8000).")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", default=str(ROOT / "sample_documents" / "appointments"))
    p.add_argument("--date", default=(date.today() + timedelta(days=1)).isoformat(), help="appointment date (default tomorrow)")
    p.add_argument("--book", action="store_true", help="also book the three appointments through the running backend")
    p.add_argument("--approve", action="store_true", help="with --book: approve them so document upload is open")
    p.add_argument("--url", default="http://127.0.0.1:8000")
    args = p.parse_args()

    out = Path(args.out)
    for s in SCENARIOS:
        write_documents(s, out / s.key, args.date)
        n = len(list((out / s.key).glob("*.png")))
        print(f"{s.key:<12} {s.title}: {n} documents in {out / s.key}")
    print(f"Documents are dated {args.date}.")
    if args.book:
        print("Booking:")
        for s in SCENARIOS:
            book(s, args.date, args.url, args.approve)
        if not args.approve:
            print("They are awaiting approval: switch to Gate admin > Approvals to approve them, then upload documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
