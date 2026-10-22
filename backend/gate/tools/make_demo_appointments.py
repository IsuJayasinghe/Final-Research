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

Every run makes NEW values (truck IDs, container numbers, booking and seal numbers, drivers, goods, vessels), so each
demo has different documents. What stays the same is each appointment's story: its goods fix the customs risk (low,
medium, high), its vessel decides whether it is delayed, and its faulty files fail in the same way. The run prints the
seed; `--seed N` makes exactly the same documents again, and `--fixed` uses the original fixed set.

Usage:
  python tools/make_demo_appointments.py [--out DIR] [--date YYYY-MM-DD] [--seed N | --fixed]   write the documents
  python tools/make_demo_appointments.py --book [--approve] [--url http://127.0.0.1:8000]       also book (and approve)

Default output: backend/gate/sample_documents/appointments/ (git-ignored). All contents are made up.
"""

import argparse
import json
import random
import string
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import vessels  # noqa: E402
from documents import assess_customs_risk, iso6346_check_digit  # noqa: E402
from tools import real_format_documents as real  # noqa: E402


def container_number(prefix_and_serial: str) -> str:
    """Owner code + serial number + the ISO 6346 check digit, e.g. 'MSCU538204' -> 'MSCU5382047'."""
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
    ),
]

# ----------------------------------------------------------------------------------------- fresh values each run

OWNERS = ["MSCU", "HLCU", "OOLU", "TCLU", "MAEU", "CMAU", "TGHU", "SEGU", "GESU", "TRLU", "HAMU", "BMOU"]
GIVEN = ["KASUN CHAMARA", "RUWAN PRASANNA", "MALITH DILSHAN", "SAMAN KUMARA", "NUWAN SAMPATH", "CHAMINDA ROSHAN",
         "ANURA BANDARA", "LAKMAL SANJEEWA", "PRASAD MADUSHAN", "ISURU THARINDA"]
SURNAMES = ["SILVA", "FERNANDO", "PERERA", "JAYAWARDENA", "WIJESINGHE", "DISSANAYAKE", "GUNASEKARA", "RATHNAYAKE"]
VEHICLES = [("TATA", "LPT 1618"), ("ISUZU", "NPR 75"), ("HINO", "FD 8J"), ("MITSUBISHI", "FUSO FJ"), ("ASHOK LEYLAND", "BOSS 1114")]

# (goods, HS code, shipper, consignee, port of discharge, address, country, [dangerous goods note lines])
CLEAN_GOODS = [  # ordinary goods: low customs risk
    ("Cotton T-shirts", "6109.10", "LANKA TEXTILES EXPORT (PVT) LTD", "NORDIC FASHION AB", "Gothenburg (SEGOT)", "Gothenburg 411 04", "SWEDEN"),
    ("Ceylon tea in bags", "0902.30", "HIGHLAND TEA EXPORTERS (PVT) LTD", "LONDON TEA TRADERS LTD", "Felixstowe (GBFXT)", "Felixstowe IP11 3SY", "UNITED KINGDOM"),
    ("Ceramic tiles", "6907.21", "ISLAND CERAMICS (PVT) LTD", "GULF BUILDING SUPPLIES LLC", "Jebel Ali (AEJEA)", "Dubai, UAE", "UNITED ARAB EMIRATES"),
    ("Rubber gloves", "4015.19", "SERENDIB RUBBER PRODUCTS (PVT) LTD", "MEDI SUPPLY GMBH", "Hamburg (DEHAM)", "Hamburg 20457", "GERMANY"),
]
HAZARD_GOODS = [  # fuels and chemicals: medium customs risk
    ("Petroleum oils", "2710.19", "CEYLON PETROCHEM TRADING (PVT) LTD", "GULF ENERGY SUPPLIES FZE", "Fujairah (AEFJR)", "Fujairah, UAE", "UNITED ARAB EMIRATES",
     ["IMDG Class 3 - Flammable liquid", "UN Number: UN 1203   Packing Group II"]),
    ("Methanol", "2905.11", "ISLAND CHEMICALS (PVT) LTD", "SOUTH ASIA SOLVENTS PTE LTD", "Singapore (SGP)", "Singapore 079903", "SINGAPORE",
     ["IMDG Class 3 - Flammable liquid", "UN Number: UN 1230   Packing Group II"]),
    ("Sodium hydroxide solution", "2815.12", "LANKA INDUSTRIAL CHEMICALS (PVT) LTD", "BAY CLEANING SUPPLIES LLC", "Jebel Ali (AEJEA)", "Dubai, UAE", "UNITED ARAB EMIRATES",
     ["IMDG Class 8 - Corrosive", "UN Number: UN 1824   Packing Group II"]),
    ("Acetone", "2914.11", "CEYLON SOLVENTS (PVT) LTD", "ORIENT COATINGS PTE LTD", "Port Klang (MYPKG)", "Port Klang 42000", "MALAYSIA",
     ["IMDG Class 3 - Flammable liquid", "UN Number: UN 1090   Packing Group II"]),
]
REEFER_GOODS = [  # alcohol: high customs risk (goods, hs, shipper, consignee, pod, address, country, set point)
    ("Wine in bottles", "2204.21", "HILL COUNTRY WINES (PVT) LTD", "ASIA BEVERAGE TRADING PTE LTD", "Singapore (SGP)", "Singapore 079903", "SINGAPORE", "+12 C"),
    ("Whisky in cases", "2208.30", "CEYLON SPIRITS (PVT) LTD", "PACIFIC SPIRITS PTE LTD", "Singapore (SGP)", "Singapore 119962", "SINGAPORE", "+15 C"),
    ("Beer in kegs", "2203.00", "ISLAND BREWERY (PVT) LTD", "MALDIVES BEVERAGES PVT LTD", "Male (MVMLE)", "Male 20026", "MALDIVES", "+4 C"),
]


def random_scenarios(seed: int) -> list[Scenario]:
    """Three appointments with fresh values. The goods fix the customs risk, the vessel fixes the delay, and the faults
    are the same as in the fixed set, so each appointment tells the same story with different documents."""
    rng = random.Random(seed)
    trucks = rng.sample(range(10000, 100000), 3)
    hours = rng.sample(range(7, 19), 3)

    def common(i: int) -> dict:
        given, (make, model) = rng.choice(GIVEN), rng.choice(VEHICLES)
        return dict(
            truck=f"TRK-{trucks[i]}", hour=hours[i],
            container=container_number(rng.choice(OWNERS) + f"{rng.randint(0, 999999):06d}"),
            booking_no=f"OPLBK{rng.randint(0, 9999999):07d}", seal=f"SL{rng.randint(0, 999999):06d}",
            voyage=f"{rng.randint(10, 260)}{rng.choice('EWNS')}", driver_given=given, driver_surname=rng.choice(SURNAMES),
            licence=f"B{rng.randint(0, 9999999):07d}", vehicle_make=make, vehicle_model=model,
            plate=f"{rng.choice(['WP', 'CP', 'SP', 'NW'])} {''.join(rng.choices(string.ascii_uppercase, k=3))}-{rng.randint(1000, 9999)}",
        )

    g = rng.choice(CLEAN_GOODS)
    clean = Scenario(
        key="1_clean", title="Clean standard export", carrier=rng.choice(["Carrier-A", "Carrier-D", "Carrier-E", "Carrier-J"]),
        container_type="standard", cargo_category="export", vessel=rng.choice(["MV EVER GRACE", "MV LANKA EXPRESS", "MAERSK COLOMBO"]),
        goods=g[0], hs=g[1], shipper=g[2], consignee=g[3], pod=g[4], pod_address=g[5], pod_country=g[6],
        weight_kg=f"{rng.randrange(12000, 26000, 10):,}", **common(0),
    )
    g = rng.choice(HAZARD_GOODS)
    hazardous = Scenario(
        key="2_hazardous", title=f"Hazardous {g[0].lower()} import, delayed vessel", carrier="Carrier-B",
        container_type="hazardous", cargo_category="import", vessel=rng.choice(["MV OCEAN PIONEER", "MV PACIFIC STAR"]),
        goods=g[0], hs=g[1], shipper=g[2], consignee=g[3], pod=g[4], pod_address=g[5], pod_country=g[6],
        cargo_note=g[7] + ["Hazard label displayed on all four sides"], weight_kg=f"{rng.randrange(18000, 27000, 10):,}",
        problems=[("vgm", "wrong_container"), ("gate_pass", "expired")], **common(1),
    )
    g = rng.choice(REEFER_GOODS)
    reefer = Scenario(
        key="3_reefer", title=f"Reefer {g[0].lower()} export, high customs scrutiny", carrier=rng.choice(["Carrier-C", "Carrier-F", "Carrier-G"]),
        container_type="reefer", cargo_category="export", vessel=rng.choice(["MV OCEAN PIONEER", "MV PACIFIC STAR"]),
        goods=g[0], hs=g[1], shipper=g[2], consignee=g[3], pod=g[4], pod_address=g[5], pod_country=g[6], tare_kg=4600,
        cargo_note=[f"Refrigerated container - Set Point: {g[7]}", "Temperature recorder calibrated"],
        weight_kg=f"{rng.randrange(16000, 26000, 10):,}",
        problems=[("seal_match", "no_seal_number"), ("driver_docs", "incomplete"), ("gate_pass", "blurry")], **common(2),
    )
    return [clean, hazardous, reefer]


PROBLEM_TEXT = {
    ("vgm", "wrong_container"): "vgm__PROBLEM_wrong_container: flagged, the container number does not match the booking",
    ("gate_pass", "expired"): "gate_pass__PROBLEM_expired: flagged, the permit is not valid on the appointment date",
    ("seal_match", "no_seal_number"): "seal_photo__PROBLEM_no_seal_number: flagged, a required detail (the seal number) is missing",
    ("driver_docs", "incomplete"): "driver_docs__PROBLEM_incomplete: flagged, no licence number and no vehicle registration",
    ("gate_pass", "blurry"): "gate_pass__PROBLEM_blurry: flagged, too blurry to be recognised as a gate pass (the system does not guess)",
}


def expectations(s: Scenario) -> list[str]:
    """What the panel should see for this appointment, worked out from its own values."""
    required = 7 if s.container_type in ("reefer", "hazardous") else 6
    out = [f"needs {required} documents" + {"hazardous": " (the dangerous goods declaration is the seventh)",
                                            "reefer": " (the reefer certificate is the seventh)"}.get(s.container_type, "")]
    out += [PROBLEM_TEXT[p] for p in s.problems]
    out.append(f"after replacing the faulty files: {required} of {required} cleared" if s.problems else f"all {required} documents are cleared")
    risk = assess_customs_risk({"hs_code": s.hs, "declaration_no": "x"})
    out.append(f"customs risk: {risk['level']} ({risk['reasons'][0]})")
    delay = vessels.DEMO_SCHEDULE.get(s.vessel, 0.0)
    line = (f"vessel {s.vessel} is delayed {delay:g} h: raises the no-show risk" if delay >= vessels.DELAY_THRESHOLD_H
            else f"vessel {s.vessel} is on schedule: no vessel delay")
    if s.carrier == "Carrier-B":
        line += " (Carrier-B is also the least reliable carrier)"
    out.append(line)
    return out


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
    lines += ["", "What you should see:"] + [f"  - {e}" for e in expectations(s)]
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
    p.add_argument("--seed", type=int, help="repeat a previous run: the same values again (the seed is printed on every run)")
    p.add_argument("--fixed", action="store_true", help="use the original fixed set (TRK-81001/2/3 ...) instead of new values")
    p.add_argument("--book", action="store_true", help="also book the three appointments through the running backend")
    p.add_argument("--approve", action="store_true", help="with --book: approve them so document upload is open")
    p.add_argument("--url", default="http://127.0.0.1:8000")
    args = p.parse_args()

    out = Path(args.out)
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(1, 1_000_000)
    scenarios = SCENARIOS if args.fixed else random_scenarios(seed)
    for s in scenarios:
        write_documents(s, out / s.key, args.date)
        n = len(list((out / s.key).glob("*.png")))
        print(f"{s.key:<12} {s.title}: {n} documents in {out / s.key}")
    print(f"Documents are dated {args.date}." + ("  Fixed set." if args.fixed else f"  Seed {seed} (--seed {seed} makes the same documents again)."))
    print(f"\nBook these as the driver (Request Appointment) for {args.date}:")
    print(f"  {'folder':<12} {'truck':<10} {'container':<12} {'carrier':<10} {'type':<10} {'cargo':<7} hour")
    for s in scenarios:
        print(f"  {s.key:<12} {s.truck:<10} {s.container:<12} {s.carrier:<10} {s.container_type:<10} {s.cargo_category:<7} {s.hour:02d}:00")
    if args.book:
        print("Booking:")
        for s in scenarios:
            book(s, args.date, args.url, args.approve)
        if not args.approve:
            print("They are awaiting approval: switch to Gate admin > Approvals to approve them, then upload documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
