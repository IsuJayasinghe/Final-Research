"""
Generate synthetic sample documents for demoing and testing the OCR document check.

Writes PNG files for one booking (a hazardous container, so the special-cargo document
is needed too) plus deliberately faulty variants:

  good set           booking_confirmation, cusdec, gate_pass, vgm, seal_photo, driver_docs, special_cargo
  faulty variants    vgm_wrong_container, seal_missing, vgm_bad_weight, gate_pass_blurry, wrong_document

All contents are made up. Usage:  python tools/make_sample_documents.py [output_dir]
Default output: backend/gate/sample_documents/ (git-ignored).
"""

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from documents import iso6346_check_digit  # noqa: E402

CONTAINER = "CSQU3054383"  # the ISO 6346 standard's own worked example (valid check digit)
OTHER_CONTAINER = "MSKU" + "123456" + str(iso6346_check_digit("MSKU123456"))
TRUCK = "TRK-80579"
SEAL = "SL884213"
APPT_DATE = "2026-10-14"

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _font(size: int, bold: bool = False):
    for p in _BOLD_CANDIDATES if bold else _FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def render(title: str, lines: list[str], path: Path, subtitle: str | None = None) -> Image.Image:
    img = Image.new("RGB", (1100, 160 + 62 * len(lines) + 60), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, img.width - 20, img.height - 20], outline="#123a5c", width=3)
    d.text((50, 45), title, font=_font(44, bold=True), fill="#123a5c")
    if subtitle:
        d.text((50, 105), subtitle, font=_font(26), fill="#444444")
    y = 170
    for line in lines:
        d.text((60, y), line, font=_font(34), fill="black")
        y += 62
    img.save(path)
    return img


def blur_and_noise(img: Image.Image, path: Path) -> None:
    rng = random.Random(3)
    small = img.resize((img.width // 4, img.height // 4)).resize(img.size).filter(ImageFilter.GaussianBlur(3))
    px = small.load()
    for _ in range(40000):
        x, y = rng.randrange(small.width), rng.randrange(small.height)
        v = rng.randrange(0, 255)
        px[x, y] = (v, v, v)
    small.save(path)


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)

    render("BOOKING CONFIRMATION", [
        "Booking No: BKG-77201944",
        f"Container No: {CONTAINER}",
        "Vessel: MV EVER GRACE   Voyage: 042E",
        "Port of Loading: Colombo   Port of Discharge: Singapore",
        f"ETD: {APPT_DATE}   Shipper: Lanka Exports Ltd",
    ], out / "booking_confirmation.png", "Sri Lanka Ports Authority - Terminal Booking")

    def cusdec(name: str, goods: str | None, hs: str | None, declaration: bool = True) -> None:
        lines = []
        if declaration:
            lines.append("Declaration No: CUS-2026-558120")
        lines.append("Customs Declaration - Export")
        lines.append("Exporter: Lanka Exports Ltd   Consignee: Pacific Imports Pte")
        if goods:
            lines.append(f"Goods: {goods}")
        if hs:
            lines.append(f"HS Code: {hs}   Duty: LKR 0.00")
        lines.append(f"Container: {CONTAINER}   Date: {APPT_DATE}")
        render("CUSTOMS CLEARANCE DOCUMENT (CUSDEC)", lines, out / f"{name}.png", "Sri Lanka Customs")

    # customs risk is derived from the declaration: medium (fuels), low (ordinary goods),
    # high (tobacco) and high (incomplete declaration: no declaration number, no HS code)
    cusdec("cusdec", "Petroleum oils", "2710.19")
    cusdec("cusdec_low_risk", "Cotton T-shirts", "6109.10")
    cusdec("cusdec_high_risk", "Cigarettes", "2402.20")
    cusdec("cusdec_incomplete", None, None, declaration=False)

    render("GATE PASS", [
        f"Truck: {TRUCK}   Vehicle No: WP CAB-1234",
        f"Container: {CONTAINER}",
        f"Valid from {APPT_DATE} 09:00   Valid until {APPT_DATE} 12:00",
        "Authorised for terminal entry - Gate In",
    ], out / "gate_pass.png", "Colombo Terminal Entry Permit")

    render("VERIFIED GROSS MASS (VGM)", [
        f"Container No: {CONTAINER}",
        "Verified Gross Mass: 24,350 kg",
        "Method 1 - weighbridge   SOLAS VI/2 declaration",
        f"Date: {APPT_DATE}",
    ], out / "vgm.png", "Weight Declaration")

    render("CONTAINER SEAL CHECK", [
        f"Container No: {CONTAINER}",
        f"Seal No: {SEAL}",
        "Seal intact - photographed at stuffing yard",
    ], out / "seal_photo.png")

    render("DRIVER AND VEHICLE DOCUMENTS", [
        "Driving Licence No: B1234567",
        "Driver: K. Perera",
        "Vehicle Registration No: WP CAB-1234",
        "Revenue Licence valid 2026",
    ], out / "driver_docs.png")

    render("DANGEROUS GOODS DECLARATION", [
        "IMDG Class 3 - Flammable liquid",
        "UN Number: UN 1203   Packing Group II",
        f"Container: {CONTAINER}",
        "Hazard label displayed on all four sides",
    ], out / "special_cargo.png")

    # ---- faulty variants
    render("VERIFIED GROSS MASS (VGM)", [
        f"Container No: {OTHER_CONTAINER}",
        "Verified Gross Mass: 24,350 kg",
        "Method 1 - weighbridge   SOLAS VI/2 declaration",
    ], out / "vgm_wrong_container.png", "Weight Declaration")

    render("CONTAINER SEAL CHECK", [
        f"Container No: {CONTAINER}",
        "Seal intact - photographed at stuffing yard",
    ], out / "seal_missing.png")

    render("VERIFIED GROSS MASS (VGM)", [
        f"Container No: {CONTAINER}",
        "Verified Gross Mass: 450 kg",
        "Method 1 - weighbridge   SOLAS VI/2 declaration",
    ], out / "vgm_bad_weight.png", "Weight Declaration")

    blurry = render("GATE PASS", [
        f"Truck: {TRUCK}   Vehicle No: WP CAB-1234",
        f"Container: {CONTAINER}",
        f"Valid until {APPT_DATE} 12:00",
    ], out / "_tmp.png", "Colombo Terminal Entry Permit")
    blur_and_noise(blurry, out / "gate_pass_blurry.png")
    (out / "_tmp.png").unlink()

    # a booking confirmation uploaded into the VGM slot
    (out / "wrong_document.png").write_bytes((out / "booking_confirmation.png").read_bytes())

    print(f"Wrote {len(list(out.glob('*.png')))} sample documents to {out}")
    print(f"Use container {CONTAINER}, truck {TRUCK}, hazardous container type, appointment date {APPT_DATE}.")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sample_documents")
