"""
Layout-aware reading of forms and tables (Component 4 document checking).

Real terminal and shipping documents are grids: the label sits in one cell and its value in the cell to the right or
directly below, and the OCR engine returns every cell as a separate text box with a position. Plain "Label: value"
regexes cannot read that, so this module works on the boxes:

  * a box is a LABEL when its text (ignoring spaces, case and a leading field number such as "13." or "S.") matches a
    known label, allowing for OCR typos ("Vestel" is read as "Vessel");
  * the VALUE is what follows the label in the same box, else the next box on the same row, else the box(es) below
    it in the same column; a neighbour that is itself a label is never taken as a value;
  * a few special readers cover things that are not "label -> value": the numbered Sri Lankan driving licence, the
    tare / cargo / gross mass row of a VGM table, and which weighing-method check box is ticked.

Nothing here runs OCR; it only interprets the boxes the OCR engine returned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class Item:
    """One OCR text box."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float = 1.0

    @property
    def h(self) -> float:
        return max(self.y1 - self.y0, 1.0)

    @property
    def w(self) -> float:
        return max(self.x1 - self.x0, 1.0)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


def items_from_ocr(result, y_offset: float = 0.0) -> list[Item]:
    """RapidOCR output [[box, text, conf], ...] -> Items."""
    items = []
    for box, text, conf in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append(Item(str(text), min(xs), min(ys) + y_offset, max(xs), max(ys) + y_offset, float(conf)))
    return items


# ----------------------------------------------------------------------------------------------- dates

_GLUED_TIME = re.compile(r"(\d{4}[-/.]\d{1,2}[-/.]\d{2})(?=\d{2}:\d{2})")
_DATE_ISO = re.compile(r"(?<!\d)(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)")
_DATE_DMY = re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?!\d)")


def unglue(text: str) -> str:
    """"2026-10-2106:00" -> "2026-10-21 06:00" (the OCR often drops the space between a date and a time)."""
    return _GLUED_TIME.sub(r"\1 ", text)


def parse_dates(text: str) -> list[str]:
    """Every date in the text as YYYY-MM-DD, in order. Copes with a time glued on by the OCR ("2026-10-2106:00")."""
    from datetime import datetime

    text = _GLUED_TIME.sub(r"\1 ", text)
    found = [(m.start(), tuple(map(int, m.groups()))) for m in _DATE_ISO.finditer(text)]
    found += [(m.start(), (int(m.group(3)), int(m.group(2)), int(m.group(1)))) for m in _DATE_DMY.finditer(text)]
    out = []
    for _, (y, mo, d) in sorted(found):
        try:
            out.append(datetime(y, mo, d).strftime("%Y-%m-%d"))
        except ValueError:
            continue
    return list(dict.fromkeys(out))


def parse_time(text: str) -> str | None:
    m = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)", _GLUED_TIME.sub(r"\1 ", text))
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


# ----------------------------------------------------------------------------------------------- labels

def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


# field -> label names, written without spaces or punctuation. A field is captured when its label is found.
CAPTURE: dict[str, tuple[str, ...]] = {
    "booking_no": ("bookingno", "bookingnumber", "bookingref", "bookingreference"),
    "vessel_voyage": ("vesselvoyage",),
    "vessel_name": ("vessel", "vesselname"),
    "voyage": ("voyageno", "voyagenumber", "voyage"),
    "port_of_loading": ("portofloading",),
    "port_of_discharge": ("portofdischarge",),
    "etd": ("sailingdateetd", "sailingdate", "etd"),
    "eta": ("arrivaldateeta", "arrivaldate", "eta"),
    "shipper": ("shipper",),
    "consignee": ("consignee",),
    "exporter": ("exporter",),
    "importer": ("importer",),
    "declaration_no": ("declarationno", "declarationnumber"),
    "declaration_date": ("dateofdeclaration",),
    "goods_description": ("goodsdescription", "descriptionofgoods"),
    "hs_code": ("hscode",),
    "seal_number": ("sealno", "sealnumber"),
    "truck_id": ("truckno", "truckid", "trucknumber"),
    "driver_name": ("drivername", "driver"),
    "valid_from": ("validfrom",),
    "valid_until": ("validto", "validuntil", "validtill"),
    "appointment_date": ("appointmentdate",),
    "gate_pass_no": ("gatepassno", "gatepassnumber"),
    "plate": ("registrationno", "vehicleno", "vehicleregistrationno", "vehicleregistration"),
    "vehicle_owner": ("owner",),
    "vehicle_make": ("make",),
    "vehicle_model": ("model",),
    "vehicle_type": ("type",),
    "vgm_ref": ("vgmrefno",),
    "signatory": ("name", "authorisedsignatory", "authorizedsignatory", "signedby"),
    "inspector": ("inspectedby",),
}

# labels that are not captured but must never be mistaken for a value
OTHER_LABELS = (
    "terminal", "entrytype", "inspectiondate", "inspectionlocation", "designation", "signature", "position", "company",
    "date", "page", "sizetype", "condition", "sealcondition", "commodity", "cargoweight", "tareweight", "grossweight",
    "grossweightkgs", "verifiedgrossmass", "totalpackages", "marksnumbers", "modeoftransport", "customsoffice",
    "countryofexport", "countryofdestination", "customsvalue", "customsvaluelkr", "containerno", "containernumber",
    "containerdetails", "bookingdetails", "additionalinformation", "freightterms", "reference", "remarks",
    "gatepassdetails", "importantinstructions", "weighingmethod", "yearofmanufacture", "engineno", "chassisno",
    "authorisedby", "containerphoto", "sealphoto", "consigneeaddress", "cargodescription", "size",
)
MULTI_LINE = {"goods_description"}  # values that may wrap onto further lines

_LABEL_NAMES: list[tuple[str, str]] = sorted(
    [(name, field) for field, names in CAPTURE.items() for name in names] + [(n, "") for n in OTHER_LABELS],
    key=lambda t: -len(t[0]),
)
_NUMBERING = re.compile(r"^\s*(?:\d{1,2}|[A-Za-z])\s*[.,]\s*(?=[A-Za-z])")
_NEXT_LABEL = re.compile(r"\s+[A-Za-z][A-Za-z ./()]{1,24}\s*[:：]")
FUZZY_MIN_LEN = 6  # shorter label names must match exactly
FUZZY_RATIO = 0.8


def _match_label(compact: str) -> tuple[str, str] | None:
    """(label name, field) when this whole compact text is a label, allowing OCR typos in longer ones."""
    for name, field in _LABEL_NAMES:
        if compact == name:
            return name, field
    for name, field in _LABEL_NAMES:
        if len(name) >= FUZZY_MIN_LEN and abs(len(compact) - len(name)) <= 3:
            if SequenceMatcher(None, compact, name).ratio() >= FUZZY_RATIO:
                return name, field
    return None


def split_label(item: Item) -> tuple[str, str] | None:
    """If the box is (or starts with) a label: (field, text already after the label in the same box, may be '')."""
    raw = item.text.strip()
    if not raw:
        return None
    stripped = _NUMBERING.sub("", raw)
    for candidate in dict.fromkeys([stripped, raw]):
        for sep in (":", "："):
            if sep in candidate:
                left, right = candidate.split(sep, 1)
                hit = _match_label(norm(left))
                if hit:
                    return hit[1], right
        hit = _match_label(norm(candidate))
        if hit:
            return hit[1], ""
        # label glued to its value by a full stop: "Booking No.MLKBC2609187"
        for name, field in _LABEL_NAMES:
            if len(name) < FUZZY_MIN_LEN or norm(candidate) == name:
                continue
            m = re.match(r"\s*" + r"[\s.]*".join(re.escape(c) for c in name) + r"\s*[.#](?=\S)", candidate, re.IGNORECASE)
            if m:
                return field, candidate[m.end():]
    return None


def is_label(item: Item) -> bool:
    return split_label(item) is not None or bool(re.match(r"^\s*\d{1,2}\s*[.,]\s*[A-Za-z]{3}", item.text))


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" :：-|.,")


# ------------------------------------------------------------------------------------------- geometry

def same_row(a: Item, b: Item) -> bool:
    overlap = min(a.y1, b.y1) - max(a.y0, b.y0)
    return overlap >= 0.45 * min(a.h, b.h)


def same_column(a: Item, b: Item) -> bool:
    overlap = min(a.x1, b.x1) - max(a.x0, b.x0)
    return overlap >= 0.25 * min(a.w, b.w)


def _right_of(items: list[Item], label: Item) -> Item | None:
    row = [i for i in items if i is not label and same_row(i, label) and i.x0 >= label.x1 - 6]
    return min(row, key=lambda i: i.x0) if row else None


def _below(items: list[Item], label: Item, max_lines: int) -> list[Item]:
    out: list[Item] = []
    last = label
    while len(out) < max_lines:
        first = not out
        below = [
            i for i in items
            if i is not last and i not in out and i.y0 >= last.y1 - 0.35 * last.h and same_column(i, label)
            and i.y0 - last.y1 <= (2.6 if first else 0.3) * last.h  # a wrapped line sits right under the previous one
            and (first or i.conf >= 0.7)
        ]
        if not below:
            break
        nxt = min(below, key=lambda i: i.y0)
        if is_label(nxt):
            break
        out.append(nxt)
        last = nxt
    return out


def value_for(items: list[Item], label: Item, remainder: str, max_lines: int = 1) -> str | None:
    """The value belonging to a label box."""
    remainder = _NEXT_LABEL.split(remainder, 1)[0] if remainder else ""
    if len(clean(remainder)) >= 3:
        return clean(remainder)
    right = _right_of(items, label)
    if right is not None and not is_label(right):
        return clean(right.text) or None
    below = _below(items, label, max_lines)
    return clean(" ".join(i.text for i in below)) or None if below else None


# ---------------------------------------------------------------------------------------- field repair

_SEAL_FIX = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2", "Q": "0"})
_SEAL_RE = re.compile(r"^([A-Z]{2,4})([0-9OILSBZQ]{5,9})$")


def repair_seal(value: str) -> str | None:
    """'SL1234S67' -> 'SL1234567' (letters read as digits in the numeric part); None when not seal-shaped."""
    compact = re.sub(r"[^A-Z0-9]", "", value.upper())
    m = _SEAL_RE.match(compact)
    return m.group(1) + m.group(2).translate(_SEAL_FIX) if m else None


def repair_plate(value: str) -> str:
    """'WPTRK-80579' / 'WP TRK - 80579' -> 'WP TRK-80579'."""
    compact = re.sub(r"[^A-Z0-9]", "", value.upper())
    m = re.match(r"^([A-Z]{2})([A-Z]{2,3})(\d{3,5})$", compact)
    if m:
        return f"{m.group(1)} {m.group(2)}-{m.group(3)}"
    m = re.match(r"^([A-Z]{2,3})(\d{4})$", compact)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return clean(value.upper())


def parse_number(text: str) -> int | None:
    """'24,000' / '3.900' (a comma misread as a full stop) / '20 100' -> an integer; None for anything else."""
    t = text.strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", t):
        return int(re.sub(r"[.,]", "", t))
    if re.fullmatch(r"\d{3,6}", t):
        return int(t)
    return None


def row_numbers(items: list[Item], anchor: Item) -> list[int]:
    """Numbers to the right of `anchor` on its row, left to right (a table row such as tare / cargo / gross mass)."""
    row = sorted((i for i in items if i is not anchor and same_row(i, anchor) and i.x0 > anchor.x1 - 4), key=lambda i: i.x0)
    return [n for n in (parse_number(i.text) for i in row) if n is not None]


# ---------------------------------------------------------------------------------- check boxes / licence

def _ink_ratio(image, box: tuple[int, int, int, int]) -> float:
    crop = image.crop(box).convert("RGB")
    px = crop.getdata()
    if not len(px):
        return 0.0
    dark = sum(1 for r, g, b in px if (r + g + b) / 3 < 150 or (b - r > 45 and b > 90))
    return dark / len(px)


def checked_method(items: list[Item], image) -> str | None:
    """Which weighing-method check box is ticked ('1' or '2'); None when both are listed but it cannot be told."""
    boxes = {}
    for it in items:
        m = re.match(r"\s*method\s*([12])\b", it.text, re.IGNORECASE)
        if m and m.group(1) not in boxes:
            boxes[m.group(1)] = it
    if len(boxes) < 2 or image is None:
        return None
    ink = {}
    for key, it in boxes.items():
        h = it.h
        # the box sits just left of the text, level with it; stay inside the text's own rows so the neighbouring box is not counted
        box = (max(int(it.x0 - 2.7 * h), 0), max(int(it.y0), 0), max(int(it.x0 - 0.2 * h), 1), int(it.y1))
        ink[key] = _ink_ratio(image, box)
    hi, lo = max(ink, key=ink.get), min(ink, key=ink.get)
    return hi if ink[hi] >= 1.25 * max(ink[lo], 0.02) else None


def has_method_choice(items: list[Item]) -> bool:
    """True when the form lists both weighing methods (a check-box choice), not just one."""
    found = {m.group(1) for it in items if (m := re.match(r"\s*method\s*([12])\b", it.text, re.IGNORECASE))}
    return len(found) == 2


_LICENCE_NUMBERS = {"1": "surname", "2": "given_names", "3": "date_of_birth", "4a": "issued", "4b": "licence_expiry", "5": "licence_no", "9": "categories"}


def read_licence(items: list[Item]) -> dict:
    """Numbered fields of a Sri Lankan driving licence card (1 surname, 2 given names, 4b expiry, 5 number ...)."""
    out: dict = {}
    for it in items:
        m = re.fullmatch(r"\s*(\d{1,2}[ab]?)\s*[.,]?\s*", it.text, re.IGNORECASE)
        if not m or m.group(1).lower() not in _LICENCE_NUMBERS:
            continue
        right = _right_of(items, it)
        if right is not None:
            out.setdefault(_LICENCE_NUMBERS[m.group(1).lower()], clean(right.text))
    if "given_names" in out and "surname" not in out:
        given = next((i for i in items if clean(i.text) == out["given_names"]), None)
        if given is not None:
            above = [
                i for i in items
                if i is not given and i.y1 <= given.y0 + 0.4 * given.h and given.y0 - i.y1 <= 1.2 * given.h
                and abs(i.x0 - given.x0) <= 0.6 * given.h and re.fullmatch(r"[A-Za-z' -]{2,30}", i.text.strip())
            ]
            if above:
                out["surname"] = clean(max(above, key=lambda i: i.y1).text)
    return out


# ------------------------------------------------------------------------------------------- the reader

def extract(items: list[Item], image=None, doc_key: str | None = None) -> dict:
    """Details read from the layout. Only keys that were actually found are present."""
    if not items:
        return {}
    ordered = sorted(items, key=lambda i: (round(i.cy / 10), i.x0))
    raw: dict[str, str] = {}
    for it in ordered:
        hit = split_label(it)
        if not hit or hit[0] not in CAPTURE or hit[0] in raw:
            continue
        field, remainder = hit
        value = value_for(items, it, remainder, 3 if field in MULTI_LINE else 1)
        if value:
            raw[field] = value

    out: dict = {}
    for key in ("booking_no", "shipper", "consignee", "exporter", "importer", "goods_description", "vgm_ref",
                "signatory", "inspector", "driver_name", "gate_pass_no", "vehicle_owner", "vehicle_make",
                "vehicle_model", "vehicle_type", "port_of_loading", "port_of_discharge"):
        if raw.get(key):
            out[key] = raw[key]
    for key in ("gate_pass_no", "booking_no"):
        if key in out:
            out[key] = re.sub(r"\s", "", out[key]).upper()

    if raw.get("vessel_voyage"):
        parts = [p.strip() for p in raw["vessel_voyage"].split("/", 1)]
        raw.setdefault("vessel_name", parts[0])
        if len(parts) > 1:
            raw.setdefault("voyage", parts[1])
    if raw.get("vessel_name"):
        out["vessel_name"] = clean(raw["vessel_name"]).upper()
    if raw.get("voyage"):
        v = re.sub(r"[^A-Z0-9]", "", raw["voyage"].upper())
        if 3 <= len(v) <= 8:
            out["voyage"] = v
    if raw.get("declaration_no"):
        out["declaration_no"] = re.sub(r"\s", "", raw["declaration_no"]).upper()
    if raw.get("hs_code"):
        digits = re.sub(r"\D", "", raw["hs_code"])
        if len(digits) >= 4:
            out["hs_code"] = digits[:4] + ("." + digits[4:6] if len(digits) > 4 else "")
    if raw.get("seal_number"):
        seal = repair_seal(raw["seal_number"])
        if seal:
            out["seal_number"] = seal
    if raw.get("truck_id"):
        m = re.search(r"TRK[\s\-]*(\d{3,6})", raw["truck_id"].upper())
        if m:
            out["truck_id"] = f"TRK-{m.group(1)}"
    if raw.get("plate"):
        out["plate"] = repair_plate(raw["plate"])

    for key in ("valid_from", "valid_until"):
        if raw.get(key):
            dates = parse_dates(raw[key])
            if dates:
                out[key] = dates[0]
            t = parse_time(raw[key])
            if t:
                out[key + "_time"] = t
    for key in ("appointment_date", "declaration_date", "etd", "eta"):
        if raw.get(key):
            dates = parse_dates(raw[key])
            if dates:
                out[key] = dates[0]

    # seal numbers printed more than once (a table and a photo) must agree
    if out.get("seal_number"):
        prefix = re.match(r"[A-Z]+", out["seal_number"]).group(0)
        seen = []
        for it in items:
            c = re.sub(r"[^A-Z0-9]", "", it.text.upper())
            if c.startswith(prefix) and (s := repair_seal(c)) and s.startswith(prefix) and s not in seen:
                seen.append(s)
        if len(seen) > 1:
            out["seal_candidates"] = seen

    # a table row that carries the container number: tare / cargo / gross mass
    if doc_key == "vgm":
        from documents import find_container_numbers  # local import: documents imports this module

        anchor = next((i for i in ordered if find_container_numbers(i.text)), None)
        numbers = row_numbers(items, anchor) if anchor else []
        if len(numbers) >= 3:
            out["tare_kg"], out["cargo_kg"], out["weight_kg"] = numbers[-3:]
        elif len(numbers) == 1:
            out["weight_kg"] = numbers[0]
        if has_method_choice(items):
            method = checked_method(items, image)
            out["method"] = method  # None when the ticked box cannot be told apart
            out["method_choice"] = True

    if doc_key == "driver_docs" or any(re.search(r"driving\s*licen", i.text, re.IGNORECASE) for i in items):
        lic = read_licence(items)
        if lic.get("licence_no"):
            m = re.search(r"[A-Z]\d{7}|[A-Z]\d{5,9}", lic["licence_no"].upper())
            if m:
                out["licence_no"] = m.group(0)
        if lic.get("licence_expiry"):
            d = parse_dates(lic["licence_expiry"])
            if d:
                out["licence_expiry"] = d[0]
        elif lic.get("licence_no") or lic.get("given_names"):
            # the "4b." box was not read: on a licence card the latest date (birth < issue < expiry) is the expiry
            on_card = parse_dates(" ".join(i.text for i in items))
            if len(on_card) >= 2:
                out["licence_expiry"] = max(on_card)
        if lic.get("surname") or lic.get("given_names"):
            out["driver_name"] = clean(f"{lic.get('given_names', '')} {lic.get('surname', '')}")
    return out
