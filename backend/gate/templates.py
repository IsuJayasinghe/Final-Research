"""
Document templates: what each pre-clearance document must contain.

After OCR has extracted the details from an upload, its template says which details are REQUIRED, which are
optional, and how each is validated (a weight in a plausible range, a gate pass that has not expired, a hazard class
between 1 and 9 ...). Evaluating the template gives a field-by-field checklist and a completeness score. A document is
*complete* only when every required detail is present and valid.

The templates are plain data (a list of FieldSpec per document), so adding a document type or a required detail is one
entry here. Nothing in this module reads files or runs OCR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

VGM_MIN_KG, VGM_MAX_KG = 1_000, 40_000
REEFER_MIN_C, REEFER_MAX_C = -40.0, 30.0

Validator = Callable[[object, dict], "str | None"]  # (value, context) -> error message, or None when fine


@dataclass(frozen=True)
class FieldSpec:
    key: str  # the key of the extracted field (documents.extract_fields)
    label: str
    hint: str  # what to look for on the document
    required: bool = True
    only_for: tuple[str, ...] | None = None  # container types this detail applies to (None = all)
    validator: Validator | None = None
    missing_code: str | None = None  # issue code raised when the detail is missing
    invalid_code: str | None = None  # issue code raised when the detail is present but wrong


@dataclass(frozen=True)
class DocumentTemplate:
    doc_key: str
    title: str
    purpose: str
    fields: tuple[FieldSpec, ...] = field(default_factory=tuple)


# ---- validators ---------------------------------------------------------------------------------

def _weight_in_range(value, ctx) -> str | None:
    if not VGM_MIN_KG <= value <= VGM_MAX_KG:
        return f"Declared weight {value:,} kg is outside the plausible range ({VGM_MIN_KG:,}-{VGM_MAX_KG:,} kg)."
    return None


def _not_expired(value, ctx) -> str | None:
    expected = ctx.get("expected_date")
    if expected and value < expected:
        return f"The pass expires on {value}, before the appointment date ({expected})."
    return None


def _pass_started(value, ctx) -> str | None:
    expected = ctx.get("expected_date")
    if expected and value > expected:
        return f"The pass is only valid from {value}, after the appointment date ({expected})."
    return None


def _same_day(value, ctx) -> str | None:
    expected = ctx.get("expected_date")
    if expected and value != expected:
        return f"The pass is for {value}, but the appointment is on {expected}."
    return None


def _licence_valid(value, ctx) -> str | None:
    expected = ctx.get("expected_date")
    if expected and value < expected:
        return f"The driving licence expires on {value}, before the appointment date ({expected})."
    return None


def _imdg_class(value, ctx) -> str | None:
    if not str(value).split(".")[0] in {str(n) for n in range(1, 10)}:
        return f"IMDG class '{value}' is not valid (must be 1-9)."
    return None


def _reefer_temperature(value, ctx) -> str | None:
    if not REEFER_MIN_C <= value <= REEFER_MAX_C:
        return f"Set point {value:g} C is outside the plausible reefer range ({REEFER_MIN_C:g} to {REEFER_MAX_C:g} C)."
    return None


def _method(value, ctx) -> str | None:
    return None if str(value) in ("1", "2") else "VGM method must be 1 or 2 (SOLAS VI/2)."


# ---- the templates ------------------------------------------------------------------------------

_CONTAINER = FieldSpec(
    "container_numbers", "Container number", "ISO 6346 code such as CSQU 305438 3",
    missing_code="container_missing",
)

TEMPLATES: dict[str, DocumentTemplate] = {
    "booking_confirmation": DocumentTemplate(
        "booking_confirmation",
        "Booking Confirmation",
        "Confirms the container is booked to a specific vessel",
        (
            FieldSpec("booking_no", "Booking number", "e.g. Booking No: BKG-77201944"),
            _CONTAINER,
            FieldSpec("vessel_name", "Vessel name", "e.g. Vessel: MV EVER GRACE"),
            FieldSpec("voyage", "Voyage number", "e.g. Voyage: 042E"),
            FieldSpec("port_of_loading", "Port of loading", "e.g. Port of Loading: Colombo"),
            FieldSpec("port_of_discharge", "Port of discharge", "e.g. Port of Discharge: Singapore"),
            FieldSpec("dates", "Sailing date (ETD)", "a date such as ETD: 2026-10-15"),
            FieldSpec("shipper", "Shipper", "the exporting company", required=False),
            FieldSpec("eta", "Arrival date (ETA)", "e.g. Arrival Date (ETA): 2026-10-24", required=False),
            FieldSpec("seal_number", "Seal number", "the seal in the container table", required=False),
        ),
    ),
    "cusdec": DocumentTemplate(
        "cusdec",
        "Customs Clearance Document (CUSDEC)",
        "Legal export/import clearance",
        (
            FieldSpec("declaration_no", "Declaration number", "e.g. Declaration No: CUS-2026-558120"),
            FieldSpec("hs_code", "HS code", "tariff classification such as HS Code: 2710.19"),
            FieldSpec("goods_description", "Goods description", "e.g. Goods: Petroleum oils"),
            FieldSpec("exporter", "Exporter", "the exporting party"),
            FieldSpec("consignee", "Consignee", "the receiving party"),
            _CONTAINER,
            FieldSpec("dates", "Declaration date", "a date on the declaration"),
            FieldSpec("importer", "Importer", "the importing party", required=False),
            FieldSpec("vessel_name", "Vessel", "e.g. 10. Vessel / Voyage", required=False),
        ),
    ),
    "gate_pass": DocumentTemplate(
        "gate_pass",
        "Gate Pass",
        "Terminal-issued entry permit for the truck and container",
        (
            FieldSpec("truck_id", "Truck ID", "e.g. Truck No: TRK-80579"),
            _CONTAINER,
            FieldSpec(
                "valid_until", "Valid until", "the date the pass expires (Valid To)", validator=_not_expired,
                invalid_code="pass_expired",
            ),
            FieldSpec(
                "valid_from", "Valid from", "the date the pass starts", required=False, validator=_pass_started,
                invalid_code="pass_not_yet_valid",
            ),
            FieldSpec(
                "appointment_date", "Appointment date", "e.g. Appointment Date: 2026-10-21", required=False,
                validator=_same_day, invalid_code="appointment_date_mismatch",
            ),
            FieldSpec("gate_pass_no", "Gate pass number", "the pass reference", required=False),
            FieldSpec("driver_name", "Driver name", "the driver named on the pass", required=False),
            FieldSpec("plate", "Vehicle registration", "e.g. Vehicle No: WP CAB-1234", required=False),
        ),
    ),
    "vgm": DocumentTemplate(
        "vgm",
        "Weight Declaration (VGM)",
        "Verified Gross Mass - legally required before loading",
        (
            _CONTAINER,
            FieldSpec(
                "weight_kg", "Verified gross mass (kg)", "e.g. Verified Gross Mass: 24,350 kg",
                validator=_weight_in_range, missing_code="weight_missing", invalid_code="weight_range",
            ),
            FieldSpec("method", "Weighing method", "the ticked method, 1 or 2 (SOLAS VI/2)", validator=_method),
            FieldSpec("dates", "Date of weighing", "a date on the declaration"),
            FieldSpec("signatory", "Authorised signatory", "who signed the declaration", required=False),
            FieldSpec("shipper", "Shipper", "the company declaring the weight", required=False),
        ),
    ),
    "seal_match": DocumentTemplate(
        "seal_match",
        "Container Number & Seal Number",
        "Photo of the container and seal for physical match verification",
        (
            _CONTAINER,
            FieldSpec("seal_number", "Seal number", "e.g. Seal No: SL884213", missing_code="seal_missing"),
        ),
    ),
    "driver_docs": DocumentTemplate(
        "driver_docs",
        "Driver / Vehicle Documents",
        "Driver's licence and vehicle registration",
        (
            FieldSpec("driver_name", "Driver name", "e.g. Driver: K. Perera"),
            FieldSpec("licence_no", "Driving licence number", "e.g. Driving Licence No: B1234567"),
            FieldSpec("plate", "Vehicle registration", "e.g. Vehicle Registration No: WP CAB-1234"),
            FieldSpec(
                "licence_expiry", "Licence valid until", "the licence expiry date (field 4b)", required=False,
                validator=_licence_valid, invalid_code="licence_expired",
            ),
            FieldSpec("vehicle_owner", "Vehicle owner", "the owner on the registration certificate", required=False),
        ),
    ),
    "special_cargo": DocumentTemplate(
        "special_cargo",
        "Special Cargo Documents",
        "Dangerous goods declaration (hazardous) or refrigeration certificate (reefer)",
        (
            _CONTAINER,
            FieldSpec("un_number", "UN number", "e.g. UN Number: UN 1203", only_for=("hazardous",), missing_code="un_missing"),
            FieldSpec(
                "imdg_class", "IMDG hazard class", "e.g. IMDG Class 3", only_for=("hazardous",),
                validator=_imdg_class, invalid_code="invalid_imdg_class",
            ),
            FieldSpec("packing_group", "Packing group", "I, II or III", only_for=("hazardous",)),
            FieldSpec(
                "temperature_c", "Set-point temperature (C)", "e.g. Set Point: -18 C", only_for=("reefer",),
                validator=_reefer_temperature, missing_code="temperature_missing", invalid_code="temperature_range",
            ),
            FieldSpec("pre_trip_inspection", "Pre-trip inspection", "evidence of a pre-trip inspection", only_for=("reefer",), required=False),
        ),
    ),
}


# ---- evaluation ---------------------------------------------------------------------------------

def _present(value) -> bool:
    return value not in (None, "", [], False)


def _display(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if value is True:
        return "yes"
    return str(value)


def applicable_fields(doc_key: str, container_type: str | None) -> list[FieldSpec]:
    template = TEMPLATES[doc_key]
    return [f for f in template.fields if f.only_for is None or container_type in f.only_for]


def evaluate_template(doc_key: str, extracted: dict, ctx: dict | None = None) -> dict:
    """Checklist of every detail the document should contain: ok / missing / invalid, plus a completeness score.

    `complete` is True only when every required detail is present and valid."""
    ctx = ctx or {}
    checklist = []
    for spec in applicable_fields(doc_key, ctx.get("container_type")):
        value = extracted.get(spec.key)
        if not _present(value):
            status, message = "missing", None
        else:
            message = spec.validator(value, ctx) if spec.validator else None
            status = "invalid" if message else "ok"
        checklist.append(
            {
                "key": spec.key,
                "label": spec.label,
                "hint": spec.hint,
                "required": spec.required,
                "status": status,
                "value": _display(value) if _present(value) else None,
                "message": message,
                "missing_code": spec.missing_code,
                "invalid_code": spec.invalid_code,
            }
        )
    required = [c for c in checklist if c["required"]]
    ok = [c for c in required if c["status"] == "ok"]
    return {
        "doc_key": doc_key,
        "title": TEMPLATES[doc_key].title,
        "fields": checklist,
        "required_total": len(required),
        "required_ok": len(ok),
        "completeness": round(len(ok) / len(required), 3) if required else 1.0,
        "complete": len(ok) == len(required),
        "missing": [c["label"] for c in required if c["status"] == "missing"],
        "invalid": [c["label"] for c in required if c["status"] == "invalid"],
    }


def describe_templates(container_type: str | None = None) -> list[dict]:
    """The templates as plain data for the UI: what each document must contain."""
    return [
        {
            "doc_key": t.doc_key,
            "title": t.title,
            "purpose": t.purpose,
            "fields": [
                {"key": f.key, "label": f.label, "hint": f.hint, "required": f.required}
                for f in applicable_fields(t.doc_key, container_type)
            ],
        }
        for t in TEMPLATES.values()
    ]
