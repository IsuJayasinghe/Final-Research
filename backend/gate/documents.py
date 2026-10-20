"""
OCR-based pre-clearance document checking (Component 4).

Pipeline for one uploaded file:
  1. read      images and scanned PDFs go through OCR (RapidOCR / ONNX, no external
               binary); digital PDFs use their embedded text layer
  2. classify  which of the required document types it looks like (weighted keywords)
  3. extract   container number (ISO 6346 check digit), seal number, VGM weight,
               booking number, truck id, plate, dates, UN number, temperature
  4. validate  against the booking (container id, truck id, date) and per-document rules
  5. verdict   cleared / flagged / unreadable, with a list of errors and warnings

Uploaded files are processed in memory only; nothing but the extracted summary is kept.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime

import layout
from templates import VGM_MAX_KG, VGM_MIN_KG, evaluate_template  # noqa: F401 (VGM limits re-exported)

MAX_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 3
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}

MIN_OCR_CONFIDENCE = 0.55  # below this the image is treated as unreadable
WARN_OCR_CONFIDENCE = 0.75
MIN_TYPE_SCORE = 3  # classification score needed to accept a document as a given type

DOCUMENT_LABELS = {
    "booking_confirmation": "Booking Confirmation",
    "cusdec": "Customs Clearance Document (CUSDEC)",
    "gate_pass": "Gate Pass",
    "vgm": "Weight Declaration (VGM)",
    "seal_match": "Container Number & Seal Number",
    "driver_docs": "Driver / Vehicle Documents",
    "special_cargo": "Special Cargo Documents",
}
BASE_DOCUMENTS = ["booking_confirmation", "cusdec", "gate_pass", "vgm", "seal_match", "driver_docs"]

# (phrase, weight): a document type's score is the sum of weights of phrases found in its text.
KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "booking_confirmation": [
        ("booking confirmation", 5), ("booking no", 2), ("booking ref", 2), ("vessel", 1),
        ("voyage", 1), ("port of loading", 2), ("port of discharge", 2), ("shipper", 1), ("etd", 1), ("eta", 1),
    ],
    "cusdec": [
        ("cusdec", 5), ("customs clearance", 4), ("customs declaration", 4), ("customs", 2), ("hs code", 2),
        ("tariff", 1), ("duty", 1), ("consignee", 1), ("importer", 1), ("exporter", 1), ("declaration no", 2),
    ],
    "gate_pass": [
        ("gate pass", 5), ("entry permit", 3), ("gate in", 1), ("valid until", 1), ("valid from", 1),
        ("authorised", 1), ("authorized", 1), ("terminal", 1), ("truck", 1), ("vehicle no", 1),
    ],
    "vgm": [
        ("verified gross mass", 5), ("vgm", 3), ("gross mass", 3), ("weighbridge", 2), ("solas", 2),
        ("weight declaration", 4), ("method 1", 1), ("method 2", 1),
    ],
    "seal_match": [("seal no", 3), ("seal number", 3), ("seal", 2), ("container no", 2), ("container number", 2)],
    "driver_docs": [
        ("driving licen", 5), ("driver licen", 5), ("driver", 2), ("licence no", 3), ("license no", 3),
        ("vehicle registration", 4), ("registration no", 3), ("revenue licen", 3), ("plate", 1), ("nic", 1),
    ],
    "special_cargo": [
        ("dangerous goods", 5), ("imdg", 4), ("un number", 3), ("hazard", 2), ("hazchem", 2),
        ("set point", 3), ("setpoint", 3), ("refrigerat", 3), ("reefer", 3), ("pre-trip", 3),
        ("temperature", 2), ("celsius", 1), ("class", 1), ("packing group", 2),
    ],
}


@dataclass
class OcrResult:
    text: str
    confidence: float  # mean line confidence, 0..1
    lines: int
    pages: int
    engine: str  # "ocr" or "pdf-text"
    items: list = field(default_factory=list)  # OCR boxes with positions (layout.Item), empty for a PDF text layer
    image: object = None  # the page image, for reading check boxes (single images only)


class DocumentError(ValueError):
    """The uploaded file cannot be processed (unsupported type, too large, corrupt)."""


# --------------------------------------------------------------------------- OCR

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def warm_up() -> None:
    """Load the OCR model (raises ImportError if RapidOCR is not installed)."""
    with _engine_lock:
        _get_engine()


def ocr_available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401

        return True
    except ImportError:
        return False


def _ocr_image(image, y_offset: float = 0.0) -> tuple[list[str], list[float], list]:
    import numpy as np

    arr = np.asarray(image.convert("RGB"))
    with _engine_lock:
        result, _ = _get_engine()(arr)
    if not result:
        return [], [], []
    return [r[1] for r in result], [float(r[2]) for r in result], layout.items_from_ocr(result, y_offset)


def read_document(data: bytes, filename: str) -> OcrResult:
    """Return the text of an image / PDF, using OCR where there is no text layer."""
    import io
    import os

    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentError(f"Unsupported file type '{ext or 'unknown'}'. Upload a PNG, JPG, WEBP, TIFF or PDF.")
    if len(data) > MAX_BYTES:
        raise DocumentError(f"File is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise DocumentError("File is empty.")

    from PIL import Image

    texts: list[str] = []
    confs: list[float] = []
    items: list = []
    page_image = None
    pages = 1
    engine = "ocr"

    if ext == ".pdf":
        import fitz  # PyMuPDF

        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as e:  # noqa: BLE001 - corrupt PDFs raise assorted errors
            raise DocumentError("Could not open this PDF.") from e
        pages = min(len(doc), MAX_PDF_PAGES)
        for i in range(pages):
            page = doc[i]
            embedded = page.get_text().strip()
            if len(embedded) > 20:  # digital PDF: use the text layer
                texts.append(embedded)
                confs.append(1.0)
                engine = "pdf-text"
            else:  # scanned PDF: render and OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                t, c, it = _ocr_image(img, y_offset=i * 10_000)
                texts.extend(t)
                confs.extend(c)
                items.extend(it)
                if pages == 1:
                    page_image = img.convert("RGB")  # a one-page scan: kept so a ticked check box can be read
    else:
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception as e:  # noqa: BLE001
            raise DocumentError("Could not read this image file.") from e
        if max(img.size) > 2200:
            img.thumbnail((2200, 2200))
        t, c, it = _ocr_image(img)
        texts.extend(t)
        confs.extend(c)
        items.extend(it)
        page_image = img.convert("RGB")

    text = "\n".join(texts)
    confidence = sum(confs) / len(confs) if confs else 0.0
    return OcrResult(
        text=text, confidence=round(confidence, 3), lines=len(confs), pages=pages, engine=engine,
        items=items, image=page_image,
    )


# ------------------------------------------------------------------ ISO 6346

_LETTER_VALUES = {}
_v = 10
for _ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    if _v % 11 == 0:  # values that are multiples of 11 are skipped
        _v += 1
    _LETTER_VALUES[_ch] = _v
    _v += 1


def iso6346_check_digit(code10: str) -> int:
    """Check digit for the first 10 characters (4 letters + 6 digits) of a container number."""
    total = 0
    for i, ch in enumerate(code10):
        value = _LETTER_VALUES[ch] if ch.isalpha() else int(ch)
        total += value * (2**i)
    return total % 11 % 10


def valid_container_number(code: str) -> bool:
    code = normalise_container(code)
    return bool(re.fullmatch(r"[A-Z]{3}[UJZ]\d{7}", code)) and iso6346_check_digit(code[:10]) == int(code[10])


def normalise_container(code: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


# ---------------------------------------------------------------- extraction

_DIGIT_FIX = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2", "Q": "0"})
_ALPHA_FIX = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z"})  # digits misread in the owner code
_CONTAINER_RE = re.compile(r"\b([A-Z0-9]{3}[UJZ])[\s\-]?([0-9OILSBZQ]{6})[\s\-]?([0-9OILSBZQ])\b")


def find_container_numbers(text: str) -> list[str]:
    found = []
    for m in _CONTAINER_RE.finditer(text.upper()):
        digits = (m.group(2) + m.group(3)).translate(_DIGIT_FIX)  # repair O/0, I/1 ... in the numeric part
        owner = m.group(1)[:3].translate(_ALPHA_FIX) + m.group(1)[3]  # ... and 0/O, 1/I in the three-letter owner code
        if not owner[:3].isalpha():
            continue
        code = owner + digits
        if code not in found:
            found.append(code)
    return found


def _parse_dates(text: str) -> list[str]:
    return layout.parse_dates(text)


def extract_fields(text: str) -> dict:
    text = layout.unglue(text)
    upper = text.upper()
    fields: dict = {}

    containers = find_container_numbers(text)
    if containers:
        fields["container_numbers"] = containers

    m = re.search(r"SEAL\s*(?:NO\.?|NUMBER|#)?\s*[:\-]?\s*([A-Z]{0,3}[\s\-]?\d{4,10})", upper)
    if m:
        fields["seal_number"] = re.sub(r"[\s\-]", "", m.group(1))

    m = re.search(r"BOOKING\s*(?:NO\.?|NUMBER|REF\.?|REFERENCE|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{5,})", upper)
    if m:
        fields["booking_no"] = m.group(1)

    kg = re.findall(r"(\d{1,3}(?:[,\s]\d{3})+|\d{3,6})(?:\.\d+)?\s*(?:KGS?|KILOGRAMS?)\b", upper)
    if kg:
        fields["weight_kg"] = int(re.sub(r"[,\s]", "", kg[0]))

    m = re.search(r"\b(TRK[\s\-]?\d{3,6})\b", upper)
    if m:
        fields["truck_id"] = re.sub(r"\s", "", m.group(1)).replace("TRK", "TRK-").replace("--", "-")

    m = re.search(r"\b([A-Z]{2,3}[\s\-][A-Z]{2,3}[\s\-]\d{4})\b", upper)  # province + letters + digits, e.g. WP CAB-1234
    if m and re.search(r"VEHICLE|REGISTRATION|PLATE|REG\.?\s*NO", upper):
        fields["plate"] = m.group(1)

    m = re.search(r"LICEN[CS]E\s*(?:NO\.?|NUMBER|#)?\s*[:\-]?\s*([A-Z]?\d{5,9})", upper)
    if m:
        fields["licence_no"] = m.group(1)

    m = re.search(r"VESSEL(?:\s*NAME)?\s*[:\-]\s*([A-Z][A-Z0-9 .\-]{2,40}?)\s*(?:VOYAGE|VOY\b|\n|$)", upper)
    if m:
        fields["vessel_name"] = re.sub(r"\s+", " ", m.group(1)).strip(" .-")

    m = re.search(r"VOYAGE\s*(?:NO\.?|NUMBER)?\s*[:\-]?\s*([A-Z0-9]{3,8})\b", upper)
    if m:
        fields["voyage"] = m.group(1)

    m = re.search(r"\bHS[\s\-]*(?:CODE)?[\s:\-]*(\d{4}(?:[.\s]?\d{2}){0,3})\b", upper)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        fields["hs_code"] = digits[:4] + ("." + digits[4:6] if len(digits) > 4 else "")

    m = re.search(r"DECLARATION\s*(?:NO\.?|NUMBER|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{5,})", upper)
    if m:
        fields["declaration_no"] = m.group(1)

    m = re.search(r"(?:GOODS|DESCRIPTION)[^:\n]{0,20}:\s*([^\n]{3,80})", text, flags=re.IGNORECASE)
    if m:
        fields["goods_description"] = m.group(1).strip()

    m = re.search(r"\bUN\s?(\d{4})\b", upper)
    if m:
        fields["un_number"] = "UN" + m.group(1)

    m = re.search(r"(?:SET\s*POINT|SETPOINT|TEMPERATURE|TEMP)[^\d\-]{0,20}(-?\d{1,2}(?:\.\d)?)\s*°?\s*C\b", upper)
    if m:
        fields["temperature_c"] = float(m.group(1))

    # ---- further details the document templates ask for
    for key, label, stop in (
        ("port_of_loading", r"PORT\s*OF\s*LOADING", r"PORT\s*OF\s*DISCHARGE"),
        ("port_of_discharge", r"PORT\s*OF\s*DISCHARGE", r"ETD|ETA|SHIPPER"),
        ("shipper", r"SHIPPER", ""),
        ("exporter", r"EXPORTER", r"CONSIGNEE"),
        ("consignee", r"CONSIGNEE", ""),
        ("driver_name", r"DRIVER(?:\s*NAME)?", ""),
        ("signatory", r"(?:AUTHORI[SZ]ED\s+SIGNATORY|SIGNED\s+BY|SIGNATORY)", ""),
    ):
        value = _labelled(text, label, stop)
        if value:
            fields[key] = value

    for key, label in (("valid_from", r"VALID\s*FROM"), ("valid_until", r"VALID\s*(?:UNTIL|TILL|TO)")):
        m = re.search(label + r"\s*[:\-]?\s*([0-9]{1,4}[-/.][0-9]{1,2}[-/.][0-9]{1,4})", upper)
        parsed = _parse_dates(m.group(1)) if m else []
        if parsed:
            fields[key] = parsed[0]

    m = re.search(r"\bMETHOD\s*([12])\b", upper)
    if m:
        fields["method"] = m.group(1)

    m = re.search(r"(?:IMDG|HAZARD|DG)\s*CLASS\s*[:\-]?\s*([1-9](?:\.[1-9])?)\b", upper)
    if not m and re.search(r"IMDG|DANGEROUS", upper):
        m = re.search(r"\bCLASS\s*[:\-]?\s*([1-9](?:\.[1-9])?)\b", upper)
    if m:
        fields["imdg_class"] = m.group(1)

    # roman numerals are often misread by OCR as l, 1 or |, so accept those and repair them (Il -> II)
    m = re.search(r"PACKING\s*GROUP\s*[:\-]?\s*([IL1|]{1,3}|[23])(?![A-Z0-9])", upper)
    if m:
        token = m.group(1)
        fields["packing_group"] = {"2": "II", "3": "III"}.get(token) or "I" * len(token)

    if re.search(r"PRE[\s\-]?TRIP", upper):
        fields["pre_trip_inspection"] = True

    for key, label in (("etd", r"(?:ETD|SAILING\s*DATE)"), ("eta", r"(?:ETA|ARRIVAL\s*DATE)")):
        m = re.search(label + r"[^0-9\n]{0,12}(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4})", upper)
        parsed = _parse_dates(m.group(1)) if m else []
        if parsed:
            fields[key] = parsed[0]

    dates = _parse_dates(text)
    if dates:
        fields["dates"] = dates
    return fields


def merge_layout(fields: dict, ocr: OcrResult, doc_key: str | None = None) -> dict:
    """Add what the OCR boxes say about forms and tables (see layout.py). Where the layout found a value it wins,
    because it knows which cell the value was in; the text patterns stay as the fallback."""
    if not ocr.items:
        return fields
    for key, value in layout.extract(ocr.items, ocr.image, doc_key).items():
        if key == "method" and value is None:
            fields.pop("method", None)  # both methods are listed and the ticked box cannot be told
        elif value not in (None, "", []):
            fields[key] = value
    return fields


def _labelled(text: str, label: str, stop: str = "") -> str | None:
    """Value after `Label:` up to the next label (`stop` regex) or the end of the line."""
    tail = rf"(?:{stop}|$)" if stop else r"$"
    m = re.search(rf"{label}\s*[:\-]\s*(.+?)\s*{tail}", text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    value = re.sub(r"\s+", " ", m.group(1)).strip(" .-")
    return value if len(value) >= 2 else None


# ------------------------------------------------------------ customs risk from the CUSDEC

# Illustrative HS-chapter risk table. A real deployment would use the customs authority's own risk profile.
HS_CHAPTER_HIGH = {
    "22": "alcohol", "24": "tobacco", "36": "explosives and pyrotechnics",
    "71": "precious stones and metals", "93": "arms and ammunition", "97": "art and antiques",
}
HS_CHAPTER_MEDIUM = {
    "27": "mineral fuels and oils", "28": "inorganic chemicals", "29": "organic chemicals",
    "30": "pharmaceuticals", "38": "chemical products", "84": "machinery", "85": "electrical equipment",
    "87": "vehicles",
}
_LEVELS = ["low", "medium", "high"]


def assess_customs_risk(fields: dict) -> dict:
    """Customs risk level (low / medium / high) and the reasons, from a CUSDEC's extracted fields."""
    reasons: list[str] = []
    hs = fields.get("hs_code")
    if hs:
        chapter = hs[:2]
        if chapter in HS_CHAPTER_HIGH:
            level = 2
            reasons.append(f"HS {hs}: {HS_CHAPTER_HIGH[chapter]} are high-scrutiny goods.")
        elif chapter in HS_CHAPTER_MEDIUM:
            level = 1
            reasons.append(f"HS {hs}: {HS_CHAPTER_MEDIUM[chapter]} get extra customs checks.")
        else:
            level = 0
            reasons.append(f"HS {hs}: ordinary goods.")
    else:
        level = 1
        reasons.append("No HS code on the declaration, so the goods cannot be risk-profiled.")
    if not fields.get("declaration_no"):
        level = min(level + 1, 2)
        reasons.append("No declaration number found; an incomplete declaration raises scrutiny.")
    return {"level": _LEVELS[level], "reasons": reasons, "hs_code": hs}


# ----------------------------------------------------------- classification

def classify(text: str, fields: dict | None = None) -> dict[str, int]:
    """Score every document type for this text."""
    lower = re.sub(r"\s+", " ", text.lower())
    compact = re.sub(r"[^a-z0-9]", "", lower)  # OCR of photographed forms often drops the spaces

    def hit(phrase: str) -> bool:
        squeezed = re.sub(r"[^a-z0-9]", "", phrase)
        return phrase in lower or (len(squeezed) >= 8 and squeezed in compact)

    scores = {key: sum(w for phrase, w in phrases if hit(phrase)) for key, phrases in KEYWORDS.items()}
    fields = fields if fields is not None else extract_fields(text)
    if fields.get("container_numbers"):
        scores["seal_match"] += 3  # a container code is the core of a container/seal photo
    return scores


def best_type(scores: dict[str, int]) -> str:
    key, score = max(scores.items(), key=lambda kv: kv[1])
    return key if score >= MIN_TYPE_SCORE else "unknown"


# ---------------------------------------------------------------- validation

def _issue(level: str, code: str, message: str) -> dict:
    return {"level": level, "code": code, "message": message}


def validate(doc_key: str, text: str, fields: dict, scores: dict, ocr_conf: float, ctx: dict) -> list[dict]:
    """Cross-checks of a document against the booking and against itself. Whether every required detail is
    present is the template's job (see check_issues)."""
    issues: list[dict] = []
    expected_label = DOCUMENT_LABELS[doc_key]
    detected = best_type(scores)

    if scores.get(doc_key, 0) < MIN_TYPE_SCORE:
        if detected != "unknown":
            issues.append(
                _issue("error", "wrong_document", f"This looks like a {DOCUMENT_LABELS[detected]}, but this slot needs the {expected_label}.")
            )
        else:
            issues.append(_issue("error", "unrecognised", f"Could not recognise this as a {expected_label}. Check you uploaded the right file."))
        return issues  # field rules would only add noise for the wrong document

    if MIN_OCR_CONFIDENCE <= ocr_conf < WARN_OCR_CONFIDENCE:
        issues.append(_issue("warning", "low_quality", f"Image quality is low (OCR confidence {ocr_conf:.0%}); a clearer scan is safer."))

    # container number: must match the booking wherever the document carries one
    expected_container = normalise_container(ctx.get("expected_container_id"))
    found = fields.get("container_numbers", [])
    if expected_container and found and expected_container not in found:
        issues.append(
            _issue("error", "container_mismatch", f"Container number on the document ({', '.join(found)}) does not match the booking ({expected_container}).")
        )
    for code in found:
        if not valid_container_number(code):
            issues.append(_issue("warning", "check_digit", f"Container number {code} fails the ISO 6346 check digit - confirm it was read correctly."))

    if doc_key == "seal_match" and len(fields.get("seal_candidates", [])) > 1:
        issues.append(_issue("error", "seal_mismatch", f"The seal number differs inside this document ({' vs '.join(fields['seal_candidates'])}); the table and the seal photo must agree."))

    if doc_key == "vgm" and all(fields.get(k) for k in ("tare_kg", "cargo_kg", "weight_kg")):
        expected_gross = fields["tare_kg"] + fields["cargo_kg"]
        if abs(expected_gross - fields["weight_kg"]) > max(50, 0.01 * fields["weight_kg"]):
            issues.append(_issue("error", "vgm_arithmetic", f"Tare {fields['tare_kg']:,} kg + cargo {fields['cargo_kg']:,} kg = {expected_gross:,} kg, but the verified gross mass says {fields['weight_kg']:,} kg."))

    if doc_key == "gate_pass":
        expected_truck = (ctx.get("expected_truck_id") or "").upper().replace(" ", "")
        if expected_truck and fields.get("truck_id") and fields["truck_id"] != expected_truck:
            issues.append(_issue("error", "truck_mismatch", f"Truck on the gate pass ({fields['truck_id']}) is not the booked truck ({expected_truck})."))
        expected_date = ctx.get("expected_date")
        if expected_date and fields.get("dates") and expected_date not in fields["dates"]:
            issues.append(_issue("warning", "date_mismatch", f"Gate pass date ({', '.join(fields['dates'])}) differs from the appointment date ({expected_date})."))
        expected_time = ctx.get("expected_time")
        start, end = fields.get("valid_from_time"), fields.get("valid_until_time")
        if expected_time and start and end and not start <= expected_time <= end:
            issues.append(_issue("warning", "outside_pass_window", f"Your slot ({expected_time}) is outside the pass window ({start} to {end})."))
    return issues


def template_issues(template: dict) -> list[dict]:
    """Errors for every REQUIRED detail of the template that is missing or invalid."""
    issues = []
    for item in template["fields"]:
        if item["status"] == "ok" or (not item["required"] and item["status"] == "missing"):
            continue
        if item["status"] == "missing":
            code = item["missing_code"] or f"missing_{item['key']}"
            issues.append(_issue("error", code, f"Missing required detail: {item['label']} ({item['hint']})."))
        else:
            code = item["invalid_code"] or f"invalid_{item['key']}"
            issues.append(_issue("error", code, item["message"] or f"{item['label']} is not valid."))
    return issues


def check_issues(doc_key: str, text: str, fields: dict, scores: dict, ocr_conf: float, ctx: dict) -> tuple[list[dict], dict | None]:
    """Everything wrong with a document: booking cross-checks plus the template's completeness checks.

    Returns (issues, template evaluation). The template is None when the document is the wrong type, because
    its details are then meaningless."""
    issues = validate(doc_key, text, fields, scores, ocr_conf, ctx)
    if any(i["code"] in ("wrong_document", "unrecognised") for i in issues):
        return issues, None
    template = evaluate_template(doc_key, fields, ctx)
    seen = {i["code"] for i in issues}
    issues += [i for i in template_issues(template) if i["code"] not in seen]
    return issues, template


def cross_check(results: dict) -> list[dict]:
    """Details that must agree ACROSS the uploaded documents. These are warnings: one document may simply be wrong or
    misread, so the driver is told to confirm, not blocked. `results` maps a slot to its check_document() result."""

    def get(doc: str, key: str):
        return ((results.get(doc) or {}).get("fields") or {}).get(key)

    def squeeze(v) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(v).upper())

    out: list[dict] = []

    def compare(doc_a: str, key_a: str, doc_b: str, key_b: str, code: str, what: str) -> None:
        a, b = get(doc_a, key_a), get(doc_b, key_b)
        if a and b and squeeze(a) != squeeze(b):
            out.append(_issue(
                "warning", code,
                f"{what} differs: {a} on the {DOCUMENT_LABELS[doc_a]} but {b} on the {DOCUMENT_LABELS[doc_b]}.",
            ))

    compare("booking_confirmation", "booking_no", "vgm", "booking_no", "booking_no_differs", "The booking number")
    compare("booking_confirmation", "seal_number", "seal_match", "seal_number", "seal_differs", "The seal number")
    compare("booking_confirmation", "vessel_name", "cusdec", "vessel_name", "vessel_differs", "The vessel")
    compare("booking_confirmation", "voyage", "cusdec", "voyage", "voyage_differs", "The voyage")
    # the driver on the gate pass ("N.M. Fernando") against the licence ("NIROSHAN MADUSANKA FERNANDO"): surname must appear
    pass_name, licence_name = get("gate_pass", "driver_name"), get("driver_docs", "driver_name")
    if pass_name and licence_name:
        surname = squeeze(re.split(r"[.\s]+", pass_name.strip())[-1])
        if len(surname) >= 3 and surname not in squeeze(licence_name):
            out.append(_issue("warning", "driver_differs", f"The driver on the Gate Pass ({pass_name}) does not match the driving licence ({licence_name})."))
    return out


def required_documents(container_type: str | None) -> list[str]:
    return BASE_DOCUMENTS + (["special_cargo"] if container_type in ("reefer", "hazardous") else [])


def check_document(data: bytes, filename: str, doc_key: str, ctx: dict | None = None) -> dict:
    """Run the full pipeline on one upload and return a JSON-serialisable verdict."""
    if doc_key not in DOCUMENT_LABELS:
        raise DocumentError(f"Unknown document slot '{doc_key}'.")
    ctx = ctx or {}
    ocr = read_document(data, filename)
    fields = merge_layout(extract_fields(ocr.text), ocr, doc_key)
    scores = classify(ocr.text, fields)

    if not ocr.text.strip() or ocr.confidence < MIN_OCR_CONFIDENCE:
        status = "unreadable"
        template = None
        issues = [_issue("error", "unreadable", "The text could not be read reliably. Upload a sharper, well-lit scan or a digital PDF.")]
    else:
        issues, template = check_issues(doc_key, ocr.text, fields, scores, ocr.confidence, ctx)
        status = "flagged" if any(i["level"] == "error" for i in issues) else "cleared"

    assessment = assess_customs_risk(fields) if doc_key == "cusdec" and status != "unreadable" else None
    return {
        "customs_assessment": assessment,
        "doc_key": doc_key,
        "label": DOCUMENT_LABELS[doc_key],
        "filename": filename,
        "status": status,
        "detected_type": best_type(scores),
        "detected_label": DOCUMENT_LABELS.get(best_type(scores)),
        "ocr_confidence": ocr.confidence,
        "engine": ocr.engine,
        "pages": ocr.pages,
        "fields": fields,
        "template": template,
        "issues": issues,
        "text_preview": ocr.text[:500],
    }
