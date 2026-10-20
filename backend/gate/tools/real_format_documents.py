"""
Draw the six pre-clearance documents in the layout of the real forms (grids, tables, check boxes, numbered cards).

This is the only document generator. Real documents are laid out as grids: a label in one cell and its value in the
cell below or beside it, a table row of weights, a ticked check box, a numbered driving licence card. These renderers
reproduce those layouts so the layout-aware OCR reader (layout.py) can be demonstrated and tested.

Each renderer can leave named details out (`omit=`), so a document that is incomplete in a known way can be made.
The special cargo certificate (dangerous goods declaration or reefer pre-trip certificate) has no real sample, so
it is drawn as a plain titled card.

All names, numbers and parties are made up, and no real company logo or photograph is drawn.
"""

from __future__ import annotations

import random
import sys
import zlib
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from documents import iso6346_check_digit  # noqa: E402

OTHER_CONTAINER = "MSKU" + "123456" + str(iso6346_check_digit("MSKU123456"))  # a valid container that is not the booked one

_REGULAR = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]
_BOLD = [r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]


def _font(size: int, bold: bool = False):
    for p in _BOLD if bold else _REGULAR:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)

NAVY, BLUE, GREY, LINE = "#123a5c", "#1f5fa8", "#555555", "#444444"
LINE_NAME = "ORIENT PACIFIC LINES (SRI LANKA) (PVT) LTD"
TERMINAL = "COLOMBO GATEWAY CONTAINER TERMINAL"


class Sheet:
    def __init__(self, w: int = 1000, h: int = 1000):
        self.img = Image.new("RGB", (w, h), "white")
        self.d = ImageDraw.Draw(self.img)
        self.w, self.h = w, h

    def text(self, x, y, s, size=26, bold=False, fill="black", anchor="la"):
        self.d.text((x, y), s, font=_font(size, bold), fill=fill, anchor=anchor)

    def box(self, x0, y0, x1, y1, width=2, outline=LINE, fill=None):
        self.d.rectangle([x0, y0, x1, y1], outline=outline, width=width, fill=fill)

    def hline(self, y, x0, x1, width=2):
        self.d.line([(x0, y), (x1, y)], fill=LINE, width=width)

    def vline(self, x, y0, y1, width=2):
        self.d.line([(x, y0), (x, y1)], fill=LINE, width=width)

    def cell(self, x, y, label, value, size=24, label_size=22, gap=34):
        """A grid cell: the label on top, its value below."""
        self.text(x, y, label, label_size, fill=GREY)
        if value:
            self.text(x, y + gap, value, size, bold=True)

    def barcode(self, x, y, w, h, seed):
        rng = random.Random(seed)
        pos = x
        while pos < x + w:
            bar = rng.choice([2, 2, 3, 4, 6])
            self.d.rectangle([pos, y, pos + bar - 1, y + h], fill="black")
            pos += bar + rng.choice([2, 3, 4])

    def qr(self, x, y, size, seed):
        rng = random.Random(seed)
        n, m = 21, size // 21
        for i in range(n):
            for j in range(n):
                finder = (i < 7 and j < 7) or (i < 7 and j > 13) or (i > 13 and j < 7)
                ring = finder and (i in (0, 6, 14, 20) or j in (0, 6, 14, 20) or (i in (2, 3, 4, 16, 17, 18) and j in (2, 3, 4, 16, 17, 18)))
                if (finder and ring) or (not finder and rng.random() < 0.5):
                    self.d.rectangle([x + j * m, y + i * m, x + (j + 1) * m - 1, y + (i + 1) * m - 1], fill="black")

    def save(self, path: Path, crop_to: int | None = None):
        self.img.crop((0, 0, self.w, crop_to or self.h)).save(path)


def _d(text: str, days: int = 0) -> str:
    return (date.fromisoformat(text) + timedelta(days=days)).isoformat()


# ------------------------------------------------------------------------------------ 1. booking confirmation

def booking_confirmation(s, out: Path, name: str, appt_date: str, container: str | None = None, omit: tuple = ()) -> None:
    """omit: any of 'voyage', 'port_of_discharge', 'etd' leaves that row off the form."""
    c = container or s.container
    sh = Sheet(950, 940)
    sh.d.polygon([(70, 60), (100, 30), (130, 60), (100, 90)], fill=BLUE)
    sh.text(145, 40, "ORIENT PACIFIC", 30, True, NAVY)
    sh.text(545, 38, "BOOKING CONFIRMATION", 30, True)
    sh.text(70, 100, LINE_NAME.title(), 20)
    sh.text(70, 128, "No. 45, Layards Road, Colombo 05", 20)
    sh.text(70, 156, "Tel: +94 11 2 555 000", 20)
    sh.text(560, 100, f"Booking No. : {s.booking_no}", 24, True)
    sh.text(560, 132, f"Date              : {_d(appt_date, -2)}", 22)
    sh.text(560, 160, "Page              : 1 of 1", 22)
    sh.box(790, 190, 900, 222)
    sh.text(845, 195, "ORIGINAL", 20, anchor="ma")
    sh.hline(205, 40, 770)
    sh.vline(520, 205, 330)
    sh.hline(330, 40, 910)
    sh.text(60, 215, "Shipper", 24, True)
    for i, line in enumerate([s.shipper, "No. 120, Industrial Zone", "Katunayake, Sri Lanka"]):
        sh.text(60, 250 + i * 28, line, 21)
    sh.text(535, 215, "Consignee", 24, True)
    for i, line in enumerate([s.consignee, "10 Anson Road", s.pod_address]):
        sh.text(535, 250 + i * 28, line, 21)
    sh.text(50, 350, "Booking Details", 26, True)
    rows = [
        ("Vessel", s.vessel), ("Voyage No.", s.voyage), ("Port of Loading", "Colombo, Sri Lanka (CMB)"),
        ("Port of Discharge", s.pod), ("Sailing Date (ETD)", appt_date), ("Arrival Date (ETA)", _d(appt_date, 3)),
    ]
    skip = {"voyage": "Voyage No.", "port_of_discharge": "Port of Discharge", "etd": "Sailing Date (ETD)"}
    rows = [r for r in rows if r[0] not in {skip[k] for k in omit}]
    for i, (label, value) in enumerate(rows):
        sh.text(55, 392 + i * 32, label, 23)
        sh.text(255, 392 + i * 32, f": {value}", 23)
    sh.barcode(560, 400, 340, 70, seed=zlib.crc32(s.booking_no.encode()) & 0xFFFF)
    sh.text(730, 478, s.booking_no, 24, anchor="ma")
    sh.hline(600, 40, 910, 1)
    sh.text(45, 612, "Container Details", 26, True)
    cols = [(45, "Container No."), (235, "Size/Type"), (350, "Commodity"), (540, "Gross Weight (KGS)"), (770, "Seal No.")]
    sh.box(40, 650, 915, 690)
    sh.box(40, 690, 915, 740)
    for x, label in cols:
        sh.text(x + 12, 660, label, 20, True)
        if x > 45:
            sh.vline(x, 650, 740, 1)
    seal = s.seal if name != "booking_confirmation__PROBLEM_no_seal" else ""
    for (x, _), value in zip(cols, [c, "40' HC", s.goods, f"{s.weight_kg}", seal]):
        sh.text(x + 12, 702, value, 23)
    sh.text(45, 780, "Additional Information", 26, True)
    for i, (label, value) in enumerate([
        ("Terminal", "Colombo Gateway Container Terminal (CGCT)"), ("Freight Terms", "FOB"),
        ("Reference", "PO-77845"), ("Remarks", "Please submit required documents prior to gate-in."),
    ]):
        sh.text(55, 822 + i * 28, label, 22)
        sh.text(250, 822 + i * 28, f": {value}", 22)
    sh.save(out / f"{name}.png")


# --------------------------------------------------------------------------------------------- 2. CUSDEC

def cusdec(s, out: Path, name: str, appt_date: str, omit: tuple = ()) -> None:
    """omit: any of 'declaration_no', 'hs_code', 'goods' leaves that box empty."""
    sh = Sheet(900, 950)
    sh.d.ellipse([40, 40, 130, 130], outline=NAVY, width=3)
    sh.text(85, 85, "SL", 30, True, NAVY, anchor="mm")
    sh.text(450, 40, "SRI LANKA CUSTOMS", 34, True, anchor="ma")
    sh.text(450, 88, "CUSTOMS DECLARATION (CUSDEC)", 28, True, anchor="ma")
    sh.text(450, 124, s.cargo_category.upper(), 26, True, anchor="ma")
    sh.box(760, 40, 860, 140)
    sh.text(810, 50, "CUSDEC", 18, anchor="ma")
    sh.text(810, 74, "A", 52, True, anchor="ma")
    sh.box(20, 165, 880, 905)
    for y in (255, 355, 455, 545, 615, 700, 790):
        sh.hline(y, 20, 880, 1)
    sh.vline(305, 165, 255, 1)
    sh.vline(540, 165, 255, 1)
    sh.vline(440, 255, 355, 1)
    sh.vline(470, 355, 455, 1)
    sh.vline(640, 355, 455, 1)
    sh.vline(240, 455, 545, 1)
    sh.vline(480, 455, 545, 1)
    sh.vline(480, 615, 790, 1)
    sh.vline(660, 700, 790, 1)
    L = 20
    sh.cell(30, 175, "1. Declaration No.", "" if "declaration_no" in omit else f"CUS-2026-{s.booking_no[-6:]}", L, 20)
    sh.cell(315, 175, "2. Date of Declaration", appt_date, L, 20)
    sh.cell(550, 175, "3. Customs Office", "COLOMBO", L, 20)
    sh.cell(30, 262, "4. Importer", s.consignee, L, 20)
    sh.text(30, 330, s.pod_address, 20)
    sh.cell(450, 262, "5. Exporter", s.shipper, L, 20)
    sh.text(450, 330, "Katunayake, Sri Lanka", 20)
    sh.cell(30, 362, "6. Consignee", s.consignee, L, 20)
    sh.text(30, 424, "Katunayake, Sri Lanka", 20)
    sh.cell(480, 362, "7. Country of Export", "SRI LANKA", L, 18)
    sh.cell(650, 362, "8. Country of Destination", s.pod_country, 17, 18)
    sh.cell(30, 462, "9. Mode of Transport", "By Sea", L, 20)
    sh.cell(250, 462, "10. Vessel / Voyage", f"{s.vessel} / {s.voyage}", 17, 20)
    sh.cell(500, 462, "11. Port of Loading", "Colombo (CMB)", L, 20)
    sh.cell(30, 552, "13. Container No.", s.container, 22, 20)
    sh.cell(390, 552, "14. Marks & Numbers", "N/M", L, 20)
    sh.cell(30, 622, "15. Total Packages", "100 Drums" if s.container_type == "hazardous" else "1,200 Cartons", L, 20)
    sh.cell(490, 622, "16. Gross Weight (KGS)", s.weight_kg, L, 19)
    sh.cell(30, 707, "17. Goods Description", "" if "goods" in omit else s.goods, L, 20)
    sh.cell(490, 707, "18. HS Code", "" if "hs_code" in omit else s.hs, L, 20)
    sh.cell(668, 707, "19. Customs Value (LKR)", "3,500,000.00", L, 17)
    sh.text(30, 804, "I declare that the particulars given", 16, fill=GREY)
    sh.text(30, 826, "in this declaration are true and complete.", 16, fill=GREY)
    sh.text(30, 848, "Goods are presented for examination.", 16, fill=GREY)
    sh.text(560, 805, "Name        : K. Perera", 20)
    sh.text(560, 835, "Designation : Customs Declarant", 20)
    sh.text(560, 865, f"Date          : {appt_date}", 20)
    sh.save(out / f"{name}.png")


# ------------------------------------------------------------------------------------------- 3. gate pass

def gate_pass(s, out: Path, name: str, appt_date: str, valid=("06:00", "18:00"), pass_dates=None, container=None) -> None:
    start_day, end_day, day = (pass_dates or (appt_date, appt_date)) + (appt_date,)
    c = container or s.container
    sh = Sheet(960, 920)
    sh.d.polygon([(70, 140), (110, 90), (230, 90), (190, 140)], fill=BLUE)
    sh.text(150, 105, "CGCT", 30, True, "white", anchor="ma")
    sh.text(290, 60, TERMINAL, 27, True)
    sh.text(290, 100, "Port of Colombo, Sri Lanka", 22)
    sh.text(290, 130, "Tel: +94 11 2 555 100  |  www.cgct.example", 20, fill=BLUE)
    sh.text(480, 190, "TERMINAL GATE PASS", 38, True, anchor="ma")
    sh.barcode(600, 250, 270, 62, seed=zlib.crc32(s.truck.encode()) & 0xFFFF)
    gp_no = f"GP{_d(appt_date).replace('-', '')}{s.booking_no[-4:]}"
    sh.text(735, 320, gp_no, 24, anchor="ma")
    sh.d.rectangle([50, 360, 910, 400], fill=BLUE)
    sh.text(70, 366, "GATE PASS DETAILS", 24, True, "white")
    sh.box(50, 400, 910, 700)
    sh.hline(500, 50, 910, 1)
    sh.hline(600, 50, 910, 1)
    sh.vline(330, 400, 700, 1)
    sh.vline(560, 400, 700, 1)
    sh.text(70, 410, "Gate Pass No.", 22)
    sh.text(345, 410, f"APT{s.booking_no[-7:]}", 22, True)
    sh.text(70, 450, "Appointment Date", 22)
    sh.text(345, 450, day, 22, True)
    sh.text(575, 410, "Terminal", 22)
    sh.text(575, 450, "CGCT - Colombo", 22, True)
    sh.qr(770, 410, 105, seed=zlib.crc32(s.truck.encode()) & 0xFF)
    sh.cell(70, 510, "Truck No.", s.truck, 24, 22, 46)
    sh.cell(345, 510, "Container No.", c, 24, 22, 38)
    sh.cell(575, 510, "Driver Name", s.driver_initials(), 24, 22, 38)
    sh.cell(70, 610, "Entry Type", "Import - Pickup" if s.cargo_category == "import" else "Export - Delivery", 24, 22, 46)
    sh.cell(345, 610, "Valid From", f"{start_day} {valid[0]}", 24, 22, 38)
    sh.cell(575, 610, "Valid To", f"{end_day} {valid[1]}", 24, 22, 38)
    sh.box(50, 730, 620, 900)
    sh.text(70, 740, "IMPORTANT INSTRUCTIONS", 22, True)
    for i, line in enumerate([
        "1. Present this gate pass and valid ID at the terminal gate.",
        "2. Container must match the booking and customs documents.",
        "3. Follow terminal safety regulations.",
        "4. This pass is valid only on the specified date.",
    ]):
        sh.text(70, 778 + i * 30, line, 19)
    sh.box(660, 730, 910, 900)
    sh.text(680, 740, "Authorised By", 20)
    sh.d.line([(700, 810), (760, 790), (800, 830), (870, 795)], fill=NAVY, width=3)
    sh.hline(860, 680, 890, 1)
    sh.text(685, 868, "Terminal Operations", 19)
    sh.save(out / f"{name}.png")


# ------------------------------------------------------------------------------------------------ 4. VGM

def vgm(s, out: Path, name: str, appt_date: str, container: str | None = None, method: str = "1", tare: int | None = None, gross: int | None = None) -> None:
    c = container or s.container
    gross = gross if gross is not None else int(s.weight_kg.replace(",", ""))
    own_tare = s.tare_kg if gross > s.tare_kg else gross // 4
    sh = Sheet(1000, 920)
    sh.text(500, 30, LINE_NAME, 26, True, anchor="ma")
    sh.text(500, 64, "No. 45, Layards Road, Colombo 05, Sri Lanka", 21, anchor="ma")
    sh.text(500, 120, "VERIFIED GROSS MASS (VGM) DECLARATION", 32, True, anchor="ma")
    sh.text(500, 164, "In accordance with SOLAS Regulation VI/2", 20, anchor="ma")
    sh.box(100, 200, 890, 335)
    sh.hline(262, 100, 890, 1)
    sh.vline(560, 200, 335, 1)
    sh.text(115, 208, "VGM Ref. No.", 20)
    sh.text(115, 232, f"VGM-2026-{s.booking_no[-6:]}", 22, True)
    sh.text(575, 215, f"Date  : {_d(appt_date, -1)}", 22, True)
    sh.text(115, 270, "Shipper", 20)
    sh.text(115, 296, s.shipper, 21, True)
    sh.text(575, 270, "Booking No.", 20)
    sh.text(575, 296, s.booking_no, 21, True)
    sh.text(100, 355, "Container Details", 24, True)
    sh.box(100, 390, 890, 480)
    sh.hline(430, 100, 890, 1)
    cols = [100, 255, 345, 520, 650, 780]
    for x in cols[1:]:
        sh.vline(x, 390, 480, 1)
    for x, label in zip(cols, ["Container No.", "Size/Type", "Cargo Description", "Tare (kg)", "Cargo (kg)", "VGM (kg)"]):
        sh.text(x + 8, 400, label, 17, True)
    for x, value in zip(cols, [c, "40' HC", s.goods[:18], f"{(tare if tare is not None else own_tare):,}", f"{gross - own_tare:,}", f"{gross:,}"]):
        sh.text(x + 8, 445, value, 20, True)
    sh.text(80, 510, "Weighing Method", 24, True)
    for i, (key, label) in enumerate([("1", "Method 1 - Weighing of packed container"), ("2", "Method 2 - Weighing of cargo and adding tare weight")]):
        y = 556 + i * 52
        sh.d.rectangle([100, y, 134, y + 34], outline=NAVY, width=3)
        if method == key:
            sh.d.line([(106, y + 18), (116, y + 28), (130, y + 6)], fill=BLUE, width=5)
        sh.text(155, y + 2, label, 23)
    sh.text(80, 680, "The declaration is verified by weighing the packed container in accordance with SOLAS", 18, fill=GREY)
    sh.text(80, 704, "Regulation VI/2. The weight above is the verified gross mass of the container.", 18, fill=GREY)
    for i, (label, value) in enumerate([("Name", "S. Jayasuriya"), ("Position", "Logistics Manager"), ("Company", s.shipper), ("Date", _d(appt_date, -1))]):
        sh.text(80, 760 + i * 34, label, 21)
        sh.text(210, 760 + i * 34, f": {value}", 21)
    sh.d.line([(640, 790), (690, 750), (720, 800), (790, 755)], fill=NAVY, width=3)
    sh.hline(830, 600, 900, 1)
    sh.text(750, 842, "Authorised Signature", 20, anchor="ma")
    sh.save(out / f"{name}.png")


# --------------------------------------------------------------------------- 5. container & seal report

def seal_report(s, out: Path, name: str, appt_date: str, with_seal: bool = True, photo_seal: str | None = None) -> None:
    sh = Sheet(950, 740)
    sh.d.polygon([(70, 40), (110, 30), (150, 60), (110, 80)], fill=BLUE)
    sh.text(170, 34, "CGCT", 26, True, NAVY)
    sh.text(340, 24, TERMINAL, 20, True)
    sh.text(340, 50, "Container Terminal", 19)
    sh.text(340, 74, "Port of Colombo, Sri Lanka", 19)
    sh.text(475, 112, "CONTAINER & SEAL VERIFICATION REPORT", 29, True, anchor="ma")
    sh.box(60, 150, 890, 178)
    sh.vline(400, 150, 178, 1)
    sh.text(70, 152, f"Inspection Date : {_d(appt_date, -1)}", 20)
    sh.text(410, 152, "Inspection Location : CGCT - Yard", 20)
    sh.box(60, 185, 890, 262)
    sh.hline(222, 60, 890, 1)
    cols = [60, 215, 350, 495, 640]
    for x in cols[1:]:
        sh.vline(x, 185, 262, 1)
    for x, label in zip(cols, ["Container No.", "Size/Type", "Condition", "Seal No.", "Seal Condition"]):
        sh.text(x + 10, 192, label, 19, True)
    for x, value in zip(cols, [s.container, "40' HC", "Good", s.seal if with_seal else "", "Intact"]):
        sh.text(x + 10, 232, value, 21, True)
    # two photo panels: the container door, and the seal
    sh.d.rectangle([60, 285, 440, 570], fill="#1c4f93")
    sh.d.rectangle([450, 285, 890, 570], fill="#2a5f9e")
    for x in (95, 175, 255, 335):
        sh.d.rectangle([x, 285, x + 12, 570], fill="#9aa7b5")
    sh.text(120, 340, s.container[:4], 36, True, "white")
    sh.text(235, 340, s.container[4:], 36, True, "white")
    sh.text(215, 392, "45G1", 30, True, "white")
    sh.text(110, 460, "MAX GROSS  32,500 KGS", 18, fill="#dce6f2")
    sh.text(110, 490, "TARE          3,900 KGS", 18, fill="#dce6f2")
    sh.d.rectangle([520, 410, 800, 480], fill="#2f7fd6", outline="#1f5fa8", width=3)
    sh.d.line([(700, 285), (700, 410)], fill="#9aa7b5", width=14)
    if with_seal:
        sh.text(660, 428, photo_seal or s.seal, 30, True, "white", anchor="ma")
    sh.text(250, 585, "Container Photo", 21, anchor="ma")
    sh.text(670, 585, "Seal Photo", 21, anchor="ma")
    sh.hline(625, 60, 890, 1)
    sh.text(70, 640, f"Inspected By   : T. Wijesinghe", 21)
    sh.text(70, 672, "Designation    : Yard Supervisor", 21)
    sh.text(520, 640, "Signature :", 21)
    sh.d.line([(640, 665), (680, 635), (710, 670), (770, 640)], fill=NAVY, width=3)
    sh.text(520, 690, f"Date        : {_d(appt_date, -1)}", 21)
    sh.save(out / f"{name}.png")


# ------------------------------------------------------------------ 6. driving licence + registration card

def driver_card(s, out: Path, name: str, appt_date: str, complete: bool = True, expiry: str | None = None) -> None:
    expiry = expiry or f"{int(appt_date[:4]) + 3}-03-10"  # valid for three more years unless a demo wants it expired
    sh = Sheet(730, 800)
    sh.d.rounded_rectangle([10, 10, 715, 385], radius=22, fill="#f1e6df", outline="#b9a89a", width=3)
    sh.text(370, 38, "DRIVING LICENCE", 36, True, "#3a3a3a", anchor="ma")
    sh.text(370, 82, "DEMOCRATIC SOCIALIST REPUBLIC OF SRI LANKA", 17, fill="#3a3a3a", anchor="ma")
    sh.d.rectangle([40, 110, 195, 285], fill="#c9ced6")  # photo placeholder (no real person drawn)
    sh.d.ellipse([85, 130, 150, 195], fill="#9aa3b0")
    sh.d.ellipse([60, 205, 175, 300], fill="#9aa3b0")
    sh.text(575, 128, "SL", 42, True, "#7a2a55")
    surname, given = s.driver_surname, s.driver_given
    issued = f"{int(expiry[:4]) - 5}{expiry[4:]}"  # a licence is valid for five years
    rows = [("1.", surname), ("2.", given), ("3.", "1991-05-14"), ("4a.", issued), ("4c.", "DEPARTMENT OF MOTOR TRAFFIC"),
            ("5.", s.licence if complete else ""), ("9.", "B6, D4")]
    y = 108
    for key, value in rows:
        sh.text(215, y, key, 21, fill="#333333")
        sh.text(255, y - 2, value, 23, True, "#222222")
        y += 36
    sh.text(425, 188, "4b.", 21, fill="#333333")
    sh.text(470, 186, expiry, 23, True, "#222222")
    sh.d.line([(55, 360), (100, 335), (130, 365), (190, 340)], fill=NAVY, width=3)

    sh.d.rounded_rectangle([10, 405, 715, 790], radius=18, fill="#f4f6f8", outline="#9aa3b0", width=3)
    sh.d.ellipse([30, 420, 90, 480], outline=NAVY, width=3)
    sh.text(380, 424, "DEPARTMENT OF MOTOR TRAFFIC", 23, True, anchor="ma")
    sh.text(380, 456, "VEHICLE REGISTRATION CERTIFICATE", 23, True, anchor="ma")
    plate = s.plate if complete else ""
    details = [("Registration No.", plate), ("Make", s.vehicle_make), ("Model", s.vehicle_model), ("Type", s.vehicle_type),
               ("Year of Manufacture", "2021"), ("Engine No.", "497TC123456"), ("Chassis No.", "MAT497TCM123456"), ("Owner", s.owner)]
    y = 505
    for label, value in details:
        sh.text(25, y, label, 21)
        sh.text(230, y, f": {value}", 22, True)
        y += 34
    sh.qr(565, 520, 126, seed=zlib.crc32(s.plate.encode()) & 0xFF)
    sh.save(out / f"{name}.png")


def special_cargo(s, out: Path, name: str, appt_date: str, omit: tuple = ()) -> None:
    """Dangerous goods declaration (hazardous) or reefer pre-trip certificate (reefer): a plain titled card, because
    no real sample of this form was available. omit: 'un_number', 'packing_group' (hazardous)."""
    c = s.container
    if s.container_type == "hazardous":
        lines = [s.cargo_note[0] if s.cargo_note else "IMDG Class 3 - Flammable liquid"]
        if "un_number" not in omit and "packing_group" not in omit:
            lines.append("UN Number: UN 1203   Packing Group II")
        elif "un_number" not in omit:
            lines.append("UN Number: UN 1203")
        elif "packing_group" not in omit:
            lines.append("Packing Group II")
        lines += [f"Container: {c}", "Hazard label displayed on all four sides"]
        title = "DANGEROUS GOODS DECLARATION"
    else:
        lines = [f"Container: {c}", "Refrigerated container - Set Point: +12 C", f"Pre-trip inspection completed {appt_date}", "Temperature recorder calibrated"]
        title = "REEFER PRE-TRIP INSPECTION CERTIFICATE"
    img = Image.new("RGB", (1100, 160 + 62 * len(lines) + 60), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, img.width - 20, img.height - 20], outline=NAVY, width=3)
    d.text((50, 45), title, font=_font(44, True), fill=NAVY)
    y = 130
    for line in lines:
        d.text((60, y), line, font=_font(34), fill="black")
        y += 62
    img.save(out / f"{name}.png")


def blur(path: Path, out_path: Path) -> None:
    img = Image.open(path)
    rng = random.Random(3)
    small = img.resize((img.width // 4, img.height // 4)).resize(img.size).filter(ImageFilter.GaussianBlur(3))
    px = small.load()
    for _ in range(40000):
        x, y = rng.randrange(small.width), rng.randrange(small.height)
        v = rng.randrange(0, 255)
        px[x, y] = (v, v, v)
    small.save(out_path)
