"""HTTP-level tests: real multipart uploads through the FastAPI app (memory storage)."""

import os

import pytest

os.environ.pop("DATABASE_URL", None)  # these tests always use the in-memory store

import documents  # noqa: E402

pytestmark = pytest.mark.skipif(not documents.ocr_available(), reason="rapidocr_onnxruntime not installed")

fastapi_testclient = pytest.importorskip("fastapi.testclient")


@pytest.fixture(scope="module")
def client():
    from main import app

    with fastapi_testclient.TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def sample_dir(tmp_path_factory):
    from tools import make_sample_documents as gen

    out = tmp_path_factory.mktemp("api_docs")
    gen.main(out)
    return out


def post_doc(client, sample_dir, name, doc_key, **form):
    path = sample_dir / f"{name}.png"
    with open(path, "rb") as f:
        return client.post(
            "/api/documents/check",
            data={"doc_key": doc_key, **form},
            files={"file": (path.name, f, "image/png")},
        )


def test_upload_without_appointment_uses_form_expectations(client, sample_dir):
    r = post_doc(client, sample_dir, "vgm", "vgm", expected_container_id="CSQU3054383")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "cleared" and body["fields"]["weight_kg"] == 24350
    assert body["fields"]["container_numbers"] == ["CSQU3054383"]


def test_mismatching_container_is_flagged_over_http(client, sample_dir):
    r = post_doc(client, sample_dir, "vgm", "vgm", expected_container_id="MSKU1234565")
    assert r.json()["status"] == "flagged"
    assert any(i["code"] == "container_mismatch" for i in r.json()["issues"])


def test_bad_uploads_are_rejected_cleanly(client):
    r = client.post("/api/documents/check", data={"doc_key": "vgm"}, files={"file": ("notes.docx", b"hello", "application/octet-stream")})
    assert r.status_code == 422 and "Unsupported" in r.json()["detail"]
    r = client.post("/api/documents/check", data={"doc_key": "bogus"}, files={"file": ("a.png", b"x", "image/png")})
    assert r.status_code == 422
    r = client.post("/api/documents/check", data={"doc_key": "vgm", "appointment_id": 9999}, files={"file": ("a.png", b"x", "image/png")})
    assert r.status_code == 404


def test_full_flow_over_http_book_check_submit(client, sample_dir):
    booking = {
        "truck_id": "TRK-80579",
        "container_id": "CSQU3054383",
        "carrier": "Carrier-B",
        "cargo_category": "export",
        "container_type": "hazardous",
        "customs_risk_flag": "high",
        "missing_documents": 3,
        "carrier_reliability": 0.54,
        "arrival_date": "2031-03-10",
        "arrival_hour": 10,
    }
    created = client.post("/api/appointments", json=booking)
    assert created.status_code == 200
    aid = created.json()["appointment"]["id"]
    before = created.json()["risk"]["p_no_show"]

    slots = {"booking_confirmation": "booking_confirmation", "cusdec": "cusdec", "gate_pass": "gate_pass", "vgm": "vgm",
             "seal_photo": "seal_match", "driver_docs": "driver_docs", "special_cargo": "special_cargo"}
    for name, slot in slots.items():
        assert post_doc(client, sample_dir, name, slot, appointment_id=aid).json()["status"] == "cleared", name

    stored = client.get(f"/api/appointments/{aid}/documents").json()
    assert set(stored) == set(slots.values())

    out = client.post(f"/api/appointments/{aid}/documents/submit")
    assert out.status_code == 200
    body = out.json()
    assert body["missing"] == 0 and body["after"]["p_no_show"] < before
    events = client.get(f"/api/appointments/{aid}/events").json()
    assert events[-1]["event_type"] == "DOCUMENTS_CHECKED"
    assert client.get("/api/appointments").json()[-1]["missing_documents"] == 0


def test_required_documents_depend_on_container_type(client):
    assert len(client.get("/api/documents/required?container_type=standard").json()) == 6
    assert len(client.get("/api/documents/required?container_type=reefer").json()) == 7
