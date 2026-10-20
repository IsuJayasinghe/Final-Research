import pytest

import documents as docs
import templates as tpl

CONTAINER = "CSQU3054383"
CTX = {"expected_container_id": CONTAINER, "expected_truck_id": "TRK-80579", "expected_date": "2026-10-15", "container_type": "hazardous"}

# a complete set of extracted details for every document type
COMPLETE = {
    "booking_confirmation": {
        "booking_no": "BKG-77201944", "container_numbers": [CONTAINER], "vessel_name": "MV EVER GRACE", "voyage": "042E",
        "port_of_loading": "Colombo", "port_of_discharge": "Singapore", "etd": "2026-10-15",
    },
    "cusdec": {
        "declaration_no": "CUS-2026-558120", "hs_code": "2710.19", "goods_description": "Petroleum oils",
        "exporter": "Lanka Exports Ltd", "consignee": "Pacific Imports Pte", "container_numbers": [CONTAINER], "dates": ["2026-10-15"],
    },
    "gate_pass": {"truck_id": "TRK-80579", "plate": "WP CAB-1234", "container_numbers": [CONTAINER], "valid_until": "2026-10-15"},
    "vgm": {"container_numbers": [CONTAINER], "weight_kg": 24350, "method": "1", "dates": ["2026-10-15"]},
    "seal_match": {"container_numbers": [CONTAINER], "seal_number": "SL884213"},
    "driver_docs": {"driver_name": "K. Perera", "licence_no": "B1234567", "plate": "WP CAB-1234"},
    "special_cargo": {"container_numbers": [CONTAINER], "un_number": "UN1203", "imdg_class": "3", "packing_group": "II"},
}


def test_every_document_slot_has_a_template():
    assert set(tpl.TEMPLATES) == set(docs.DOCUMENT_LABELS)
    for key, template in tpl.TEMPLATES.items():
        assert template.title == docs.DOCUMENT_LABELS[key]
        assert any(f.required for f in template.fields)


@pytest.mark.parametrize("doc_key", sorted(COMPLETE))
def test_a_document_with_all_required_details_is_complete(doc_key):
    r = tpl.evaluate_template(doc_key, COMPLETE[doc_key], CTX)
    assert r["complete"] and r["completeness"] == 1.0 and r["missing"] == [] and r["invalid"] == []
    assert r["required_ok"] == r["required_total"]


@pytest.mark.parametrize("doc_key", sorted(COMPLETE))
def test_removing_any_required_detail_makes_the_document_incomplete(doc_key):
    required = [f for f in tpl.applicable_fields(doc_key, "hazardous") if f.required]
    for spec in required:
        details = {k: v for k, v in COMPLETE[doc_key].items() if k != spec.key}
        r = tpl.evaluate_template(doc_key, details, CTX)
        assert not r["complete"], f"{doc_key} should be incomplete without {spec.key}"
        assert spec.label in r["missing"]
        assert r["completeness"] == round((len(required) - 1) / len(required), 3)


def test_optional_details_do_not_affect_completeness():
    with_optional = dict(COMPLETE["vgm"], signatory="K. Perera")
    r = tpl.evaluate_template("vgm", COMPLETE["vgm"], CTX)
    assert r["complete"]
    assert tpl.evaluate_template("vgm", with_optional, CTX)["completeness"] == r["completeness"] == 1.0
    optional = [f for f in r["fields"] if not f["required"]]
    assert optional and optional[0]["status"] == "missing"  # listed in the checklist, but harmless


def test_checklist_lists_every_detail_with_its_value_and_status():
    r = tpl.evaluate_template("booking_confirmation", {**COMPLETE["booking_confirmation"], "voyage": None}, CTX)
    by_key = {f["key"]: f for f in r["fields"]}
    assert by_key["vessel_name"]["status"] == "ok" and by_key["vessel_name"]["value"] == "MV EVER GRACE"
    assert by_key["voyage"]["status"] == "missing" and by_key["voyage"]["value"] is None
    assert by_key["container_numbers"]["value"] == CONTAINER
    assert by_key["voyage"]["hint"].startswith("e.g.")


# ---- conditional details and validators ----------------------------------------------------------

def test_special_cargo_needs_different_details_for_hazardous_and_reefer():
    haz = {f.key for f in tpl.applicable_fields("special_cargo", "hazardous") if f.required}
    reefer = {f.key for f in tpl.applicable_fields("special_cargo", "reefer") if f.required}
    assert {"un_number", "imdg_class", "packing_group"} <= haz and "temperature_c" not in haz
    assert reefer == {"container_numbers", "temperature_c"}
    reefer_doc = {"container_numbers": [CONTAINER], "temperature_c": -18.0}
    assert tpl.evaluate_template("special_cargo", reefer_doc, dict(CTX, container_type="reefer"))["complete"]
    assert not tpl.evaluate_template("special_cargo", reefer_doc, CTX)["complete"]  # a hazardous booking needs the UN details


@pytest.mark.parametrize(
    "doc_key,key,value,expected_message",
    [
        ("vgm", "weight_kg", 450, "outside the plausible range"),
        ("vgm", "weight_kg", 95000, "outside the plausible range"),
        ("vgm", "method", "3", "must be 1 or 2"),
        ("gate_pass", "valid_until", "2020-01-01", "expires on 2020-01-01"),
        ("special_cargo", "imdg_class", "0", "not valid"),
        ("special_cargo", "imdg_class", "12", "not valid"),
    ],
)
def test_a_present_but_wrong_detail_is_invalid_not_missing(doc_key, key, value, expected_message):
    r = tpl.evaluate_template(doc_key, {**COMPLETE[doc_key], key: value}, CTX)
    item = next(f for f in r["fields"] if f["key"] == key)
    assert item["status"] == "invalid" and expected_message in item["message"]
    assert not r["complete"] and item["label"] in r["invalid"]


def test_reefer_set_point_must_be_plausible():
    ctx = dict(CTX, container_type="reefer")
    ok = tpl.evaluate_template("special_cargo", {"container_numbers": [CONTAINER], "temperature_c": -18.0}, ctx)
    hot = tpl.evaluate_template("special_cargo", {"container_numbers": [CONTAINER], "temperature_c": 55.0}, ctx)
    assert ok["complete"] and not hot["complete"] and hot["invalid"] == ["Set-point temperature (C)"]


def test_gate_pass_expiry_uses_the_appointment_date():
    details = COMPLETE["gate_pass"]
    assert tpl.evaluate_template("gate_pass", details, dict(CTX, expected_date="2026-10-15"))["complete"]
    assert not tpl.evaluate_template("gate_pass", details, dict(CTX, expected_date="2026-10-16"))["complete"]
    assert tpl.evaluate_template("gate_pass", details, {"container_type": "standard"})["complete"]  # no date to compare with


def test_describe_templates_for_the_ui():
    out = tpl.describe_templates("reefer")
    assert [t["doc_key"] for t in out][0] == "booking_confirmation" and len(out) == 7
    cargo = next(t for t in out if t["doc_key"] == "special_cargo")
    assert [f["key"] for f in cargo["fields"] if f["required"]] == ["container_numbers", "temperature_c"]
    assert all({"key", "label", "hint", "required"} <= set(f) for t in out for f in t["fields"])


# ---- integration with the document check -----------------------------------------------------------

def issue_codes(doc_key, fields, ctx=CTX, text="x"):
    scores = {doc_key: 99}
    issues, template = docs.check_issues(doc_key, text, fields, scores, 0.95, ctx)
    return {i["code"] for i in issues if i["level"] == "error"}, template


def test_missing_details_become_errors_with_the_templates_own_codes():
    fields = {k: v for k, v in COMPLETE["vgm"].items() if k not in ("weight_kg", "method")}
    codes, template = issue_codes("vgm", fields)
    assert codes == {"weight_missing", "missing_method"} and not template["complete"]


def test_complete_document_has_no_errors_and_a_complete_template():
    codes, template = issue_codes("seal_match", COMPLETE["seal_match"])
    assert codes == set() and template["complete"]


def test_wrong_document_gets_no_template_checklist():
    issues, template = docs.check_issues("vgm", "booking text", {}, {"booking_confirmation": 9, "vgm": 0}, 0.9, CTX)
    assert [i["code"] for i in issues] == ["wrong_document"] and template is None


def test_no_duplicate_issue_codes():
    fields = {"container_numbers": ["MSKU1234565"], "weight_kg": 450, "method": "1", "dates": ["2026-10-15"]}
    issues, _ = docs.check_issues("vgm", "x", fields, {"vgm": 99}, 0.9, CTX)
    codes = [i["code"] for i in issues]
    assert len(codes) == len(set(codes)) and {"container_mismatch", "weight_range"} <= set(codes)


# ---- real OCR on the sample documents --------------------------------------------------------------

ocr = pytest.mark.skipif(not docs.ocr_available(), reason="rapidocr_onnxruntime not installed")


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    from doc_fixtures import make_samples

    day = CTX["expected_date"]
    return make_samples(tmp_path_factory.mktemp("tpl_samples"), day), day


def verdict(samples, name, slot, container_type="hazardous"):
    out, day = samples
    path = out / f"{name}.png"
    ctx = dict(CTX, expected_date=day, container_type=container_type)
    return docs.check_document(path.read_bytes(), path.name, slot, ctx)


@ocr
@pytest.mark.parametrize(
    "name,slot,ctype",
    [
        ("booking_confirmation", "booking_confirmation", "hazardous"),
        ("cusdec", "cusdec", "hazardous"),
        ("gate_pass", "gate_pass", "hazardous"),
        ("vgm", "vgm", "hazardous"),
        ("seal_photo", "seal_match", "hazardous"),
        ("driver_docs", "driver_docs", "hazardous"),
        ("special_cargo", "special_cargo", "hazardous"),
        ("special_cargo_reefer", "special_cargo", "reefer"),
    ],
)
def test_ocr_extracts_every_required_detail_from_a_complete_document(samples, name, slot, ctype):
    r = verdict(samples, name, slot, ctype)
    assert r["status"] == "cleared", [i["message"] for i in r["issues"]]
    t = r["template"]
    assert t["complete"] and t["completeness"] == 1.0 and t["required_ok"] == t["required_total"]


@ocr
@pytest.mark.parametrize(
    "name,slot,ctype,missing",
    [
        ("booking_confirmation_incomplete", "booking_confirmation", "hazardous", {"Voyage number", "Port of discharge", "Sailing date (ETD)"}),
        ("driver_docs_incomplete", "driver_docs", "hazardous", {"Driving licence number", "Vehicle registration"}),
        ("special_cargo_incomplete", "special_cargo", "hazardous", {"UN number", "Packing group"}),
        ("cusdec_incomplete", "cusdec", "hazardous", {"Declaration number", "HS code", "Goods description"}),
    ],
)
def test_ocr_names_exactly_which_details_an_incomplete_document_lacks(samples, name, slot, ctype, missing):
    r = verdict(samples, name, slot, ctype)
    assert r["status"] == "flagged"
    assert set(r["template"]["missing"]) == missing
    assert 0 < r["template"]["completeness"] < 1


@ocr
def test_ocr_flags_an_expired_gate_pass_as_invalid(samples):
    r = verdict(samples, "gate_pass_expired", "gate_pass")
    assert r["status"] == "flagged" and r["template"]["invalid"] == ["Valid until"]
    assert any(i["code"] == "pass_expired" for i in r["issues"])
