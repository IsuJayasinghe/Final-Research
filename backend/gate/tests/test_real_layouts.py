"""Reading real form layouts: grids, tables, check boxes, the numbered driving licence (layout.py + documents.py)."""

from pathlib import Path

import pytest

import documents
import layout
from layout import Item
from tools import make_demo_appointments as demo
from tools import real_format_documents as real

ocr_needed = pytest.mark.skipif(not documents.ocr_available(), reason="rapidocr_onnxruntime not installed")
DATE = "2030-01-07"
S = demo.SCENARIOS[1]  # hazardous
CTX = {"expected_container_id": S.container, "expected_truck_id": S.truck, "expected_date": DATE,
       "expected_time": "10:00", "container_type": S.container_type}


def box(text, x, y, w=120, h=26, conf=0.9):
    return Item(text, x, y, x + w, y + h, conf)


# ---- the reader on hand-made boxes (no OCR needed) -----------------------------------------------------------

def test_a_label_with_an_ocr_typo_is_still_found_and_its_value_taken_from_the_right():
    items = [box("Vestel", 50, 100, 60), box(":MAERSKCOLOMBO", 200, 100, 190), box("Voyage No.", 50, 140, 100), box("：2610E", 200, 140, 80)]
    out = layout.extract(items)
    assert out["vessel_name"] == "MAERSKCOLOMBO" and out["voyage"] == "2610E"


def test_a_value_under_a_header_is_found_when_the_neighbour_to_the_right_is_another_label():
    items = [box("Seal No.", 500, 190, 70), box("Seal Condition", 630, 190, 110), box("SL1234S67", 495, 228, 90), box("Intact", 660, 228, 50)]
    assert layout.extract(items)["seal_number"] == "SL1234567"  # the S read for a 5 is repaired


def test_a_date_with_a_time_glued_on_is_split():
    items = [box("Valid From", 350, 593), box("Valid To", 575, 585), box("2026-10-2106:00", 352, 624, 180), box("2026-10-2118:00", 577, 619, 180)]
    out = layout.extract(items)
    assert (out["valid_from"], out["valid_from_time"]) == ("2026-10-21", "06:00")
    assert (out["valid_until"], out["valid_until_time"]) == ("2026-10-21", "18:00")
    assert layout.parse_dates("Date 2026-10-2106:00 and 05/11/2026") == ["2026-10-21", "2026-11-05"]


def test_numbered_labels_and_a_label_glued_to_its_value():
    items = [box("S.Exporter", 446, 249, 80), box("LANKAEXPORTSLTD", 465, 269, 180), box("10.Vessel / Voyage", 246, 469, 160),
             box("MAERSKCOLOMBO/2610E", 262, 499, 260), box("BookingNo.MLKBC2609187", 577, 91, 300)]
    out = layout.extract(items)
    assert out["exporter"] == "LANKAEXPORTSLTD"
    assert (out["vessel_name"], out["voyage"]) == ("MAERSKCOLOMBO", "2610E")
    assert out["booking_no"] == "MLKBC2609187"


def test_a_page_title_is_not_mistaken_for_a_label():
    out = layout.extract([box("DRIVER AND VEHICLE DOCUMENTS", 50, 40, 400), box("Revenue Licence valid 2026", 50, 100, 300)])
    assert "driver_name" not in out


def test_a_wrapped_goods_description_stops_before_unrelated_text():
    items = [box("17.GoodsDescription", 28, 719, 160), box("Petroleum oils and oils obtained", 53, 741, 400, 28),
             box("minerals", 52, 768, 90, 28), box("garbled declaration text", 14, 810, 400, 29, conf=0.6)]
    assert layout.extract(items)["goods_description"] == "Petroleum oils and oils obtained minerals"


def test_tare_cargo_and_gross_mass_are_read_from_the_container_row_and_must_add_up():
    items = [box("MAEU3483419", 100, 463, 140), box("40'HC", 268, 464, 64), box("Petroleum oils", 377, 461, 124),
             box("3.900", 569, 462, 57), box("20,100", 704, 456, 71), box("24,000", 855, 451, 76)]
    out = layout.extract(items, doc_key="vgm")
    assert (out["tare_kg"], out["cargo_kg"], out["weight_kg"]) == (3900, 20100, 24000)  # "3.900" is 3,900


def test_licence_surname_is_taken_from_above_when_its_number_was_not_read():
    items = [box("DRIVINGLICENCE", 224, 40, 240), box("FERNANDO", 252, 103, 106), box("2.", 214, 135, 21), box("NIROSHANMADUSANKA", 254, 128, 220),
             box("5.", 215, 257, 19), box("B9123456", 255, 250, 111), box("4b.", 425, 191, 33), box("2029-03-10", 470, 185, 115)]
    out = layout.extract(items, doc_key="driver_docs")
    assert out["driver_name"] == "NIROSHANMADUSANKA FERNANDO" and out["licence_no"] == "B9123456" and out["licence_expiry"] == "2029-03-10"


def test_repairs():
    assert layout.repair_seal("SL1234S67") == "SL1234567" and layout.repair_seal("not a seal") is None
    assert layout.repair_plate(":WPTRK-80579".strip(":")) == "WP TRK-80579" and layout.repair_plate("WP CAB-1234") == "WP CAB-1234"
    assert [layout.parse_number(t) for t in ("24,000", "3.900", "450", "40'HC", "SL12")] == [24000, 3900, 450, None, None]
    assert documents.find_container_numbers("Container O0LU6198420") == ["OOLU6198420"]  # a zero read for the letter O


def test_a_vessel_name_read_without_spaces_is_restored_to_the_known_name():
    import vessels

    assert vessels.normalise_vessel("MAERSKCOLOMBO") == "MAERSK COLOMBO"
    assert vessels.normalise_vessel("M/V Ever Grace") == "MV EVER GRACE"
    assert vessels.get_vessel_delay("MAERSKCOLOMBO", "2026-10-21")["delayed"] is False


def test_documents_that_disagree_with_each_other_get_a_warning():
    results = {
        "booking_confirmation": {"fields": {"booking_no": "MLKBC2609187", "seal_number": "SL1234567", "vessel_name": "MAERSK COLOMBO", "voyage": "2610E"}},
        "vgm": {"fields": {"booking_no": "MEDKSL2609187"}},
        "seal_match": {"fields": {"seal_number": "SL7654321"}},
        "cusdec": {"fields": {"vessel_name": "MAERSKCOLOMBO", "voyage": "2610E"}},  # same vessel, spaces lost: no warning
        "gate_pass": {"fields": {"driver_name": "N.M.Fernando"}},
        "driver_docs": {"fields": {"driver_name": "NIROSHANMADUSANKA PERERA"}},
    }
    codes = {c["code"] for c in documents.cross_check(results)}
    assert codes == {"booking_no_differs", "seal_differs", "driver_differs"}
    assert all(c["level"] == "warning" for c in documents.cross_check(results))
    results["vgm"]["fields"]["booking_no"] = "mlkbc 2609187"
    results["seal_match"]["fields"]["seal_number"] = "SL1234567"
    results["driver_docs"]["fields"]["driver_name"] = "NIROSHANMADUSANKA FERNANDO"
    assert documents.cross_check(results) == []


def test_classification_ignores_missing_spaces():
    scores = documents.classify("BOOKINGCONFIRMATION\nPortof Loading :Colombo\nPortof Discharge :Singapore")
    assert documents.best_type(scores) == "booking_confirmation"


# ---- the generated real-format documents, read back by OCR -----------------------------------------------------

def check(path: Path, slot: str, **ctx):
    return documents.check_document(path.read_bytes(), path.name, slot, {**CTX, **ctx})


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    out = tmp_path_factory.mktemp("real")
    s = S
    real.vgm(s, out, "vgm2", DATE, method="2")
    real.vgm(s, out, "vgm_sum", DATE, tare=5200)
    real.seal_report(s, out, "seal_two", DATE, photo_seal="SL999999")
    real.driver_card(s, out, "licence_old", DATE, expiry="2019-03-10")
    real.gate_pass(s, out, "pass_window", DATE, valid=("12:00", "18:00"))
    real.gate_pass(s, out, "pass_future", DATE, pass_dates=("2031-01-01", "2031-01-02"))
    real.gate_pass(s, out, "pass_good", DATE)
    real.driver_card(s, out, "licence_good", DATE)
    return out


@ocr_needed
def test_the_ticked_weighing_method_is_the_one_read(made):
    assert check(made / "vgm2.png", "vgm")["fields"]["method"] == "2"


@ocr_needed
def test_tare_plus_cargo_must_equal_the_gross_mass(made):
    r = check(made / "vgm_sum.png", "vgm")
    assert r["status"] == "flagged" and "vgm_arithmetic" in {i["code"] for i in r["issues"]}


@ocr_needed
def test_two_different_seal_numbers_in_one_report_are_flagged(made):
    r = check(made / "seal_two.png", "seal_match")
    assert r["status"] == "flagged" and "seal_mismatch" in {i["code"] for i in r["issues"]}


@ocr_needed
def test_an_expired_driving_licence_is_flagged_and_a_valid_one_is_not(made):
    old = check(made / "licence_old.png", "driver_docs")
    assert old["status"] == "flagged" and "licence_expired" in {i["code"] for i in old["issues"]}
    good = check(made / "licence_good.png", "driver_docs")
    assert good["status"] == "cleared" and good["fields"]["licence_expiry"] == "2033-03-10"


@ocr_needed
def test_a_slot_outside_the_pass_window_is_a_warning_and_a_pass_for_another_day_is_an_error(made):
    window = check(made / "pass_window.png", "gate_pass")  # slot 10:00, pass 12:00 to 18:00
    assert window["status"] == "cleared" and "outside_pass_window" in {i["code"] for i in window["issues"]}
    assert "outside_pass_window" not in {i["code"] for i in check(made / "pass_good.png", "gate_pass")["issues"]}
    future = check(made / "pass_future.png", "gate_pass")
    assert future["status"] == "flagged" and "pass_not_yet_valid" in {i["code"] for i in future["issues"]}


@ocr_needed
@pytest.mark.parametrize("scenario", demo.SCENARIOS, ids=lambda s: s.key)
def test_every_real_format_document_is_read_and_cleared(scenario, tmp_path):
    demo.write_documents(scenario, tmp_path, DATE, "real")
    ctx = {"expected_container_id": scenario.container, "expected_truck_id": scenario.truck, "expected_date": DATE,
           "container_type": scenario.container_type}
    for slot in documents.required_documents(scenario.container_type):
        path = tmp_path / f"{demo.SLOT_FILES[slot]}.png"
        r = documents.check_document(path.read_bytes(), path.name, slot, ctx)
        assert r["status"] == "cleared", (slot, r["issues"])
        assert r["template"]["complete"], (slot, r["template"]["missing"])
    # the details come from the right cells
    cusdec = documents.check_document((tmp_path / "cusdec.png").read_bytes(), "cusdec.png", "cusdec", ctx)["fields"]
    assert cusdec["hs_code"] == scenario.hs and cusdec["exporter"].upper() == scenario.shipper.upper()
    gate = documents.check_document((tmp_path / "gate_pass.png").read_bytes(), "gate_pass.png", "gate_pass", ctx)["fields"]
    assert gate["truck_id"] == scenario.truck and gate["valid_from_time"] == "06:00" and gate["valid_until_time"] == "18:00"
