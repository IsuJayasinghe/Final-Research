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
from dataclasses import dataclass
from datetime import datetime

MAX_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 3
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}

MIN_OCR_CONFIDENCE = 0.55  # below this the image is treated as unreadable
WARN_OCR_CONFIDENCE = 0.75
MIN_TYPE_SCORE = 3  # classification score needed to accept a document as a given type
VGM_MIN_KG, VGM_MAX_KG = 1_000, 40_000

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


def _ocr_image(image) -> tuple[list[str], list[float]]:
    import numpy as np

    arr = np.asarray(image.convert("RGB"))
    with _engine_lock:
        result, _ = _get_engine()(arr)
    if not result:
        return [], []
    return [r[1] for r in result], [float(r[2]) for r in result]


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
                t, c = _ocr_image(img)
                texts.extend(t)
                confs.extend(c)
    else:
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception as e:  # noqa: BLE001
            raise DocumentError("Could not read this image file.") from e
        if max(img.size) > 2200:
            img.thumbnail((2200, 2200))
        t, c = _ocr_image(img)
        texts.extend(t)
        confs.extend(c)

    text = "\n".join(texts)
    confidence = sum(confs) / len(confs) if confs else 0.0
    return OcrResult(text=text, confidence=round(confidence, 3), lines=len(confs), pages=pages, engine=engine)


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
_CONTAINER_RE = re.compile(r"\b([A-Z]{3}[UJZ])[\s\-]?([0-9OILSBZQ]{6})[\s\-]?([0-9OILSBZQ])\b")
_DATE_ISO = re.compile(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b")
_DATE_DMY = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")


def find_container_numbers(text: str) -> list[str]:
    found = []
    for m in _CONTAINER_RE.finditer(text.upper()):
        digits = (m.group(2) + m.group(3)).translate(_DIGIT_FIX)  # repair O/0, I/1 ... in the numeric part
        code = m.group(1) + digits
        if code not in found:
            found.append(code)
    return found


def _parse_dates(text: str) -> list[str]:
    out = []
    for m in _DATE_ISO.finditer(text):
        y, mo, d = map(int, m.groups())
        out.append((y, mo, d))
    for m in _DATE_DMY.finditer(text):
        d, mo, y = map(int, m.groups())
        out.append((y, mo, d))
    iso = []
    for y, mo, d in out:
        try:
            iso.append(datetime(y, mo, d).strftime("%Y-%m-%d"))
        except ValueError:
            continue
    return list(dict.fromkeys(iso))


def extract_fields(text: str) -> dict:
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

    m = re.search(r"\b([A-Z]{2,3}[\s\-][A-Z]{2,3}[\s\-]\d{4}|[A-Z]{2,3}[\s\-]\d{4})\b", upper)
    if m and re.search(r"VEHICLE|REGISTRATION|PLATE|REG\.?\s*NO", upper):
        fields["plate"] = m.group(1)

    m = re.search(r"LICEN[CS]E\s*(?:NO\.?|NUMBER|#)?\s*[:\-]?\s*([A-Z]?\d{5,9})", upper)
    if m:
        fields["licence_no"] = m.group(1)

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

    dates = _parse_dates(text)
    if dates:
        fields["dates"] = dates
    return fields


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
    scores = {key: sum(w for phrase, w in phrases if phrase in lower) for key, phrases in KEYWORDS.items()}
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

    # container number: must match the booking where the document carries one
    expected_container = normalise_container(ctx.get("expected_container_id"))
    found = fields.get("container_numbers", [])
    needs_container = doc_key in ("booking_confirmation", "vgm", "seal_match", "gate_pass")
    if expected_container:
        if found and expected_container not in found:
            issues.append(
                _issue("error", "container_mismatch", f"Container number on the document ({', '.join(found)}) does not match the booking ({expected_container}).")
            )
        elif not found and needs_container:
            issues.append(_issue("error", "container_missing", "No container number could be read on this document."))
    for code in found:
        if not valid_container_number(code):
            issues.append(_issue("warning", "check_digit", f"Container number {code} fails the ISO 6346 check digit - confirm it was read correctly."))

    if doc_key == "vgm":
        kg = fields.get("weight_kg")
        if kg is None:
            issues.append(_issue("error", "weight_missing", "No verified gross mass (kg) found."))
        elif not VGM_MIN_KG <= kg <= VGM_MAX_KG:
            issues.append(_issue("error", "weight_range", f"Declared weight {kg:,} kg is outside the plausible range ({VGM_MIN_KG:,}-{VGM_MAX_KG:,} kg)."))

    if doc_key == "seal_match" and not fields.get("seal_number"):
        issues.append(_issue("error", "seal_missing", "No seal number found. The seal must be visible and readable."))

    if doc_key == "gate_pass":
        expected_truck = (ctx.get("expected_truck_id") or "").upper().replace(" ", "")
        if expected_truck and fields.get("truck_id") and fields["truck_id"] != expected_truck:
            issues.append(_issue("error", "truck_mismatch", f"Truck on the gate pass ({fields['truck_id']}) is not the booked truck ({expected_truck})."))
        expected_date = ctx.get("expected_date")
        if expected_date and fields.get("dates") and expected_date not in fields["dates"]:
            issues.append(_issue("warning", "date_mismatch", f"Gate pass date ({', '.join(fields['dates'])}) differs from the appointment date ({expected_date})."))

    if doc_key == "cusdec":
        if not fields.get("hs_code"):
            issues.append(_issue("warning", "hs_missing", "No HS code found on the customs document; customs risk is treated as medium."))
        if not fields.get("declaration_no"):
            issues.append(_issue("warning", "declaration_missing", "No declaration number found on the customs document."))

    if doc_key == "driver_docs" and not (fields.get("licence_no") or fields.get("plate")):
        issues.append(_issue("error", "driver_ids_missing", "No driving licence number or vehicle registration found."))

    if doc_key == "special_cargo":
        ctype = ctx.get("container_type")
        if ctype == "hazardous" and not fields.get("un_number"):
            issues.append(_issue("error", "un_missing", "Dangerous goods declaration needs a UN number."))
        if ctype == "reefer" and fields.get("temperature_c") is None:
            issues.append(_issue("warning", "temperature_missing", "No set-point temperature found on the reefer document."))
    return issues


def required_documents(container_type: str | None) -> list[str]:
    return BASE_DOCUMENTS + (["special_cargo"] if container_type in ("reefer", "hazardous") else [])


def check_document(data: bytes, filename: str, doc_key: str, ctx: dict | None = None) -> dict:
    """Run the full pipeline on one upload and return a JSON-serialisable verdict."""
    if doc_key not in DOCUMENT_LABELS:
        raise DocumentError(f"Unknown document slot '{doc_key}'.")
    ctx = ctx or {}
    ocr = read_document(data, filename)
    fields = extract_fields(ocr.text)
    scores = classify(ocr.text, fields)

    if not ocr.text.strip() or ocr.confidence < MIN_OCR_CONFIDENCE:
        status = "unreadable"
        issues = [_issue("error", "unreadable", "The text could not be read reliably. Upload a sharper, well-lit scan or a digital PDF.")]
    else:
        issues = validate(doc_key, ocr.text, fields, scores, ocr.confidence, ctx)
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
        "issues": issues,
        "text_preview": ocr.text[:500],
    }
