"""The three OCR demo appointments behave exactly as tools/make_demo_appointments.py and the guide say."""

from datetime import datetime

import pytest

import documents
import ml_models
import noshow
from repository import MemoryRepository
from service import GateService
from tools import make_demo_appointments as demo

DATE = "2030-01-07"
NOW = datetime(2030, 1, 7, 6, 30)
ocr_needed = pytest.mark.skipif(not documents.ocr_available(), reason="rapidocr_onnxruntime not installed")
SCENARIOS = {s.key: s for s in demo.SCENARIOS}


@pytest.fixture(scope="module", autouse=True)
def _models():
    ml_models.load_models()
    noshow.load_model()


@pytest.fixture(scope="module")
def docs_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("appointments")
    for s in demo.SCENARIOS:
        demo.write_documents(s, out / s.key, DATE)
    return out


@pytest.fixture
def svc():
    return GateService(MemoryRepository(), require_approval=True)


def book(svc, s):
    a = svc.create(dict(truck_id=s.truck, container_id=s.container, carrier=s.carrier, container_type=s.container_type,
                        cargo_category=s.cargo_category, arrival_date=DATE, arrival_hour=s.hour), now=NOW)["appointment"]
    svc.approve(a["id"])
    return a["id"]


def upload(svc, docs_dir, s, aid, slot, name):
    path = docs_dir / s.key / f"{name}.png"
    return svc.check_document(path.read_bytes(), path.name, slot, appointment_id=aid)


def test_the_three_appointments_are_different():
    assert len({s.truck for s in demo.SCENARIOS}) == 3
    assert len({s.container for s in demo.SCENARIOS}) == 3
    assert {s.container_type for s in demo.SCENARIOS} == {"standard", "hazardous", "reefer"}
    for s in demo.SCENARIOS:
        assert s.container[-1] == str(documents.iso6346_check_digit(s.container[:-1]))  # valid ISO 6346


def test_every_scenario_folder_has_its_documents_and_a_readme(docs_dir):
    for s in demo.SCENARIOS:
        names = {p.name for p in (docs_dir / s.key).iterdir()}
        slots = documents.required_documents(s.container_type)
        assert {f"{demo.SLOT_FILES[k]}.png" for k in slots} <= names
        assert "README.txt" in names
        for slot, what in s.problems:
            assert f"{demo.SLOT_FILES[slot]}__PROBLEM_{what}.png" in names
        assert s.truck in (docs_dir / s.key / "README.txt").read_text(encoding="utf-8")


@ocr_needed
@pytest.mark.parametrize("key", list(SCENARIOS))
def test_good_documents_clear_and_problem_documents_are_flagged(svc, docs_dir, key):
    s = SCENARIOS[key]
    aid = book(svc, s)
    for slot, what in s.problems:
        result = upload(svc, docs_dir, s, aid, slot, f"{demo.SLOT_FILES[slot]}__PROBLEM_{what}")
        assert result["status"] == "flagged", (slot, what, result["issues"])
    for slot in documents.required_documents(s.container_type):
        assert upload(svc, docs_dir, s, aid, slot, demo.SLOT_FILES[slot])["status"] == "cleared", slot  # replaces problems
    out = svc.submit_documents(aid)
    assert out["missing"] == 0 and out["cleared"] == len(documents.required_documents(s.container_type))


@ocr_needed
def test_each_appointment_gets_its_own_customs_risk_and_vessel(svc, docs_dir):
    seen = {}
    for s in demo.SCENARIOS:
        aid = book(svc, s)
        for slot in documents.required_documents(s.container_type):
            upload(svc, docs_dir, s, aid, slot, demo.SLOT_FILES[slot])
        out = svc.submit_documents(aid)
        a = svc.repo.get(aid)
        seen[s.key] = (a.customs_risk_flag, a.vessel_name, a.vessel_delay, out["after"]["p_no_show"])
    assert [seen[k][0] for k in ("1_clean", "2_hazardous", "3_reefer")] == ["low", "medium", "high"]
    assert seen["1_clean"][1] == "MV EVER GRACE" and seen["1_clean"][2] is False
    assert seen["2_hazardous"][1] == "MV OCEAN PIONEER" and seen["2_hazardous"][2] is True
    assert seen["3_reefer"][1] == "MV PACIFIC STAR" and seen["3_reefer"][2] is True
    assert seen["1_clean"][3] < seen["2_hazardous"][3]  # clean standard export is the least risky
