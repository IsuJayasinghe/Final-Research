import pytest

import documents as docs

CONTAINER = "CSQU3054383"  # ISO 6346 worked example
CTX = {
    "expected_container_id": CONTAINER,
    "expected_truck_id": "TRK-80579",
    "expected_date": "2026-10-14",
    "container_type": "hazardous",
}


# ---- ISO 6346 ---------------------------------------------------------------

def test_check_digit_matches_the_standards_worked_example():
    assert docs.iso6346_check_digit("CSQU305438") == 3
    assert docs.valid_container_number("CSQU3054383")
    assert docs.valid_container_number("csqu 305438 3")  # spacing / case tolerant
    assert not docs.valid_container_number("CSQU3054384")
    assert not docs.valid_container_number("CSQ3054383")  # wrong shape


def test_letter_values_skip_multiples_of_eleven():
    assert docs._LETTER_VALUES["A"] == 10 and docs._LETTER_VALUES["B"] == 12 and docs._LETTER_VALUES["L"] == 23


# ---- extraction ---------------------------------------------------------------

def test_extracts_core_fields():
    f = docs.extract_fields(
        "GATE PASS Truck: TRK-80579 Vehicle No: WP CAB-1234\nContainer: CSQU 305438 3  Seal No: SL884213\n"
        "Valid until 2026-10-14 VGM Gross Mass: 24,350 kg Booking No: BKG-77201944 UN 1203"
    )
    assert f["container_numbers"] == [CONTAINER]
    assert f["seal_number"] == "SL884213"
    assert f["weight_kg"] == 24350
    assert f["truck_id"] == "TRK-80579"
    assert f["plate"] == "WP CAB-1234"
    assert f["booking_no"] == "BKG-77201944"
    assert f["un_number"] == "UN1203"
    assert f["dates"] == ["2026-10-14"]


def test_repairs_common_ocr_digit_confusions_in_container_numbers():
    assert docs.find_container_numbers("Container CSQU3O54383") == [CONTAINER]  # O read for 0
    assert docs.find_container_numbers("CSQU 3054 383 and CSQU3054383") == [CONTAINER]  # duplicates collapse


def test_dates_in_day_first_format_are_normalised():
    assert docs.extract_fields("Valid 14/10/2026")["dates"] == ["2026-10-14"]


# ---- classification -----------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("BOOKING CONFIRMATION Booking No: BKG1234567 Vessel MV X Port of Loading Colombo", "booking_confirmation"),
        ("CUSTOMS CLEARANCE DOCUMENT CUSDEC HS Code 2710 Duty", "cusdec"),
        ("GATE PASS Entry permit Valid until", "gate_pass"),
        ("VERIFIED GROSS MASS VGM weighbridge SOLAS", "vgm"),
        ("Driving Licence No B1234567 Vehicle Registration No WP CAB-1234", "driver_docs"),
        ("DANGEROUS GOODS DECLARATION IMDG UN Number UN 1203", "special_cargo"),
        ("Container No CSQU3054383 Seal No SL884213", "seal_match"),
        ("a shopping list with milk and eggs", "unknown"),
    ],
)
def test_classifies_each_document_type(text, expected):
    assert docs.best_type(docs.classify(text)) == expected


# ---- validation rules ---------------------------------------------------------

def run(doc_key, text, conf=0.9, ctx=None):
    fields = docs.extract_fields(text)
    issues, _template = docs.check_issues(doc_key, text, fields, docs.classify(text, fields), conf, ctx if ctx is not None else CTX)
    return issues


def codes(issues, level=None):
    return {i["code"] for i in issues if level is None or i["level"] == level}


def test_clean_vgm_has_no_errors():
    text = f"VERIFIED GROSS MASS VGM Container {CONTAINER} 24,350 kg Method 1 weighbridge SOLAS Date 2026-10-14"
    assert codes(run("vgm", text), "error") == set()


def test_container_on_document_must_match_the_booking():
    issues = run("vgm", "VERIFIED GROSS MASS VGM Container MSKU1234565 24,350 kg")
    assert "container_mismatch" in codes(issues, "error")


def test_missing_container_number_is_an_error_where_required():
    assert "container_missing" in codes(run("vgm", "VERIFIED GROSS MASS VGM 24,350 kg"), "error")
    assert "container_missing" in codes(run("cusdec", "CUSTOMS CLEARANCE CUSDEC HS Code 2710 Duty"), "error")  # now required


def test_vgm_weight_must_be_present_and_plausible():
    assert "weight_missing" in codes(run("vgm", f"VERIFIED GROSS MASS VGM {CONTAINER}"), "error")
    assert "weight_range" in codes(run("vgm", f"VERIFIED GROSS MASS VGM {CONTAINER} 450 kg"), "error")
    assert "weight_range" in codes(run("vgm", f"VERIFIED GROSS MASS VGM {CONTAINER} 95,000 kg"), "error")


def test_seal_number_required_on_seal_document():
    assert "seal_missing" in codes(run("seal_match", f"Container No {CONTAINER}"), "error")
    assert "seal_missing" not in codes(run("seal_match", f"Container No {CONTAINER} Seal No SL884213"))


def test_wrong_document_reports_only_the_real_problem():
    issues = run("vgm", "BOOKING CONFIRMATION Booking No: BKG1234567 Vessel Port of Loading")
    assert codes(issues) == {"wrong_document"}


def test_unrecognised_document():
    assert codes(run("gate_pass", "lorem ipsum dolor sit amet")) == {"unrecognised"}


def test_gate_pass_truck_and_date_checks():
    base = "GATE PASS Entry permit Container CSQU3054383 "
    assert "truck_mismatch" in codes(run("gate_pass", base + "Truck TRK-11111 Valid until 2026-10-14"), "error")
    assert "date_mismatch" in codes(run("gate_pass", base + "Truck TRK-80579 Valid until 2026-10-20"), "warning")
    complete = base + "Truck TRK-80579 Vehicle No: WP CAB-1234 Valid until 2026-10-14"
    assert codes(run("gate_pass", complete), "error") == set()


def test_special_cargo_requirements_depend_on_container_type():
    assert "un_missing" in codes(run("special_cargo", "DANGEROUS GOODS DECLARATION IMDG Class 3"), "error")
    reefer = dict(CTX, container_type="reefer")
    assert "temperature_missing" in codes(run("special_cargo", f"REEFER Pre-trip refrigeration certificate {CONTAINER}", ctx=reefer), "error")
    assert "temperature_missing" not in codes(run("special_cargo", f"REEFER pre-trip Set Point -18 C {CONTAINER}", ctx=reefer))


def test_check_digit_failure_is_only_a_warning_and_low_quality_is_flagged():
    text = "VERIFIED GROSS MASS VGM Container CSQU3054384 24,350 kg Method 1 weighbridge SOLAS Date 2026-10-14"
    issues = run("vgm", text, conf=0.6, ctx=dict(CTX, expected_container_id="CSQU3054384"))
    assert "check_digit" in codes(issues, "warning") and "low_quality" in codes(issues, "warning")
    assert codes(issues, "error") == set()


def test_required_documents_by_container_type():
    assert len(docs.required_documents("standard")) == 6
    assert docs.required_documents("hazardous")[-1] == "special_cargo"
    assert docs.required_documents("reefer")[-1] == "special_cargo"


# ---- file handling ------------------------------------------------------------

def test_rejects_unsupported_empty_and_oversized_files():
    with pytest.raises(docs.DocumentError):
        docs.read_document(b"x", "notes.docx")
    with pytest.raises(docs.DocumentError):
        docs.read_document(b"", "scan.png")
    with pytest.raises(docs.DocumentError):
        docs.read_document(b"0" * (docs.MAX_BYTES + 1), "scan.png")
    with pytest.raises(docs.DocumentError):
        docs.read_document(b"not really an image", "scan.png")


# ---- real OCR on generated sample documents -------------------------------------

ocr = pytest.mark.skipif(not docs.ocr_available(), reason="rapidocr_onnxruntime not installed")


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    from tools import make_sample_documents as gen

    out = tmp_path_factory.mktemp("samples")
    gen.main(out)
    return out


def check(samples, name, slot):
    path = samples / f"{name}.png"
    return docs.check_document(path.read_bytes(), path.name, slot, CTX)


@ocr
@pytest.mark.parametrize(
    "name,slot",
    [
        ("booking_confirmation", "booking_confirmation"),
        ("cusdec", "cusdec"),
        ("gate_pass", "gate_pass"),
        ("vgm", "vgm"),
        ("seal_photo", "seal_match"),
        ("driver_docs", "driver_docs"),
        ("special_cargo", "special_cargo"),
    ],
)
def test_ocr_clears_every_genuine_sample(samples, name, slot):
    r = check(samples, name, slot)
    assert r["status"] == "cleared", r["issues"]
    assert r["detected_type"] == slot and r["ocr_confidence"] > 0.7


@ocr
@pytest.mark.parametrize(
    "name,slot,expected_code",
    [
        ("vgm_wrong_container", "vgm", "container_mismatch"),
        ("seal_missing", "seal_match", "seal_missing"),
        ("vgm_bad_weight", "vgm", "weight_range"),
        ("wrong_document", "vgm", "wrong_document"),
    ],
)
def test_ocr_flags_each_faulty_sample_for_the_right_reason(samples, name, slot, expected_code):
    r = check(samples, name, slot)
    assert r["status"] == "flagged"
    assert expected_code in {i["code"] for i in r["issues"]}


@ocr
def test_ocr_degraded_scan_is_not_cleared(samples):
    assert check(samples, "gate_pass_blurry", "gate_pass")["status"] in ("flagged", "unreadable")


@ocr
def test_ocr_reads_a_pdf_made_from_an_image(samples):
    import fitz

    pdf = fitz.open()
    page = pdf.new_page(width=600, height=400)
    page.insert_image(page.rect, filename=str(samples / "vgm.png"))
    r = docs.check_document(pdf.tobytes(), "vgm.pdf", "vgm", CTX)
    assert r["status"] == "cleared" and r["engine"] == "ocr"


def test_digital_pdf_uses_its_text_layer_without_ocr():
    import fitz

    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((50, 80), f"VERIFIED GROSS MASS (VGM)  Container No: {CONTAINER}  Verified Gross Mass: 24,350 kg")
    page.insert_text((50, 110), "Method 1 - weighbridge  SOLAS VI/2 declaration  Date: 2026-10-14")
    r = docs.check_document(pdf.tobytes(), "vgm.pdf", "vgm", CTX)
    assert r["engine"] == "pdf-text" and r["ocr_confidence"] == 1.0 and r["status"] == "cleared"


# ---- customs risk derived from the CUSDEC --------------------------------------------------

def test_extracts_hs_code_declaration_number_and_goods():
    f = docs.extract_fields("CUSTOMS CLEARANCE CUSDEC\nDeclaration No: CUS-2026-558120\nGoods: Petroleum oils\nHS Code: 2710.19")
    assert f["hs_code"] == "2710.19" and f["declaration_no"] == "CUS-2026-558120" and f["goods_description"] == "Petroleum oils"
    assert docs.extract_fields("HS Code 6109")["hs_code"] == "6109"


@pytest.mark.parametrize(
    "hs,level",
    [("6109.10", "low"), ("8501.10", "medium"), ("2710.19", "medium"), ("2402.20", "high"), ("9302.00", "high")],
)
def test_customs_risk_by_hs_chapter(hs, level):
    assert docs.assess_customs_risk({"hs_code": hs, "declaration_no": "CUS-1234"})["level"] == level


def test_incomplete_declaration_raises_customs_risk():
    assert docs.assess_customs_risk({"hs_code": "6109.10"})["level"] == "medium"  # ordinary goods, no declaration no.
    no_hs = docs.assess_customs_risk({"declaration_no": "CUS-1234"})
    assert no_hs["level"] == "medium" and "No HS code" in no_hs["reasons"][0]
    assert docs.assess_customs_risk({})["level"] == "high"  # nothing usable on the declaration


def test_cusdec_without_hs_code_or_declaration_number_is_incomplete():
    issues = run("cusdec", "CUSTOMS CLEARANCE DOCUMENT CUSDEC Customs Declaration Exporter Consignee")
    assert {"missing_hs_code", "missing_declaration_no"} <= codes(issues, "error")


@ocr
@pytest.mark.parametrize(
    "name,level",
    [("cusdec", "medium"), ("cusdec_low_risk", "low"), ("cusdec_high_risk", "high"), ("cusdec_incomplete", "high")],
)
def test_ocr_derives_customs_risk_from_each_declaration(samples, name, level):
    r = check(samples, name, "cusdec")
    assert r["customs_assessment"]["level"] == level  # derived even when the declaration is incomplete
    assert r["status"] == ("flagged" if name == "cusdec_incomplete" else "cleared")


@ocr
def test_non_customs_documents_carry_no_customs_assessment(samples):
    assert check(samples, "vgm", "vgm")["customs_assessment"] is None


# ---- vessel name read from the booking confirmation ---------------------------------------

def test_extracts_vessel_and_voyage():
    f = docs.extract_fields("BOOKING CONFIRMATION\nVessel: MV EVER GRACE   Voyage: 042E\nPort of Loading: Colombo")
    assert f["vessel_name"] == "MV EVER GRACE" and f["voyage"] == "042E"
    assert docs.extract_fields("VESSEL NAME - MV PACIFIC STAR")["vessel_name"] == "MV PACIFIC STAR"


def test_the_word_vessel_in_ordinary_text_is_not_a_vessel_name():
    assert "vessel_name" not in docs.extract_fields("no vessel line here, just words")


@ocr
@pytest.mark.parametrize(
    "name,vessel", [("booking_confirmation", "MV EVER GRACE"), ("booking_confirmation_delayed_vessel", "MV OCEAN PIONEER")]
)
def test_ocr_reads_the_vessel_name_from_the_booking_confirmation(samples, name, vessel):
    r = check(samples, name, "booking_confirmation")
    assert r["status"] == "cleared" and r["fields"]["vessel_name"] == vessel
