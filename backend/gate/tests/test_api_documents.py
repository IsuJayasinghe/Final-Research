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
    from doc_fixtures import make_samples

    return make_samples(tmp_path_factory.mktemp("api_docs"), "2031-03-10")  # the date of the booking made in the full-flow test


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

    # documents are locked until the gate admin approves the request
    locked = post_doc(client, sample_dir, "vgm", "vgm", appointment_id=aid)
    assert locked.status_code == 409 and "gate admin approves" in locked.json()["detail"]
    assert client.post(f"/api/appointments/{aid}/approve").status_code == 200

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


def test_derived_condition_endpoints(client):
    carriers = client.get("/api/carriers").json()
    assert len(carriers) == 10 and {"carrier", "reliability", "past_no_show_rate"} <= set(carriers[0])
    assert next(c for c in carriers if c["carrier"] == "Carrier-B")["reliability"] < 0.6

    w = client.get("/api/weather?date=2031-03-10").json()  # far beyond the forecast range
    assert w["severity"] is None and w["source"] == "beyond-forecast-range"

    v = client.get("/api/vessel-delay?vessel=MV OCEAN PIONEER&date=2031-03-10").json()
    assert v["delay_hours"] == 5.0 and v["delayed"] is True


def test_booking_over_http_needs_no_conditions_typed_in(client):
    r = client.post("/api/appointments", json={
        "truck_id": "TRK-1", "container_id": "CSQU3054383", "carrier": "Carrier-B", "cargo_category": "export",
        "container_type": "hazardous", "arrival_date": "2031-03-11", "arrival_hour": 10,
    })
    assert r.status_code == 200
    a = r.json()["appointment"]
    assert 0.45 < a["carrier_reliability"] < 0.6 and a["customs_risk_flag"] is None and a["vessel_delay"] is None
    assert r.json()["conditions"]["carrier"]["reliability_used"] == a["carrier_reliability"]


def test_templates_endpoint_lists_what_each_document_must_contain(client):
    out = client.get("/api/documents/templates?container_type=hazardous").json()
    assert len(out) == 7 and all(t["needed"] for t in out)
    cargo = next(t for t in out if t["doc_key"] == "special_cargo")
    assert {"un_number", "imdg_class", "packing_group"} <= {f["key"] for f in cargo["fields"] if f["required"]}
    standard = client.get("/api/documents/templates?container_type=standard").json()
    assert next(t for t in standard if t["doc_key"] == "special_cargo")["needed"] is False
    reefer = next(t for t in client.get("/api/documents/templates?container_type=reefer").json() if t["doc_key"] == "special_cargo")
    assert "temperature_c" in {f["key"] for f in reefer["fields"]}


def test_upload_returns_the_template_checklist_over_http(client, sample_dir):
    r = post_doc(client, sample_dir, "vgm", "vgm", expected_container_id="CSQU3054383", container_type="hazardous")
    t = r.json()["template"]
    assert t["complete"] and t["required_ok"] == t["required_total"] == 4
    assert {f["key"] for f in t["fields"]} >= {"container_numbers", "weight_kg", "method", "dates"}
    bad = post_doc(client, sample_dir, "booking_confirmation_incomplete", "booking_confirmation", expected_container_id="CSQU3054383")
    body = bad.json()
    assert body["status"] == "flagged" and "Voyage number" in body["template"]["missing"]


def test_monitor_endpoints_over_http(client):
    prof = client.get("/api/congestion/profile?date=2031-03-12").json()
    assert len(prof) == 24 and {"hour", "max_lane_queue", "status", "booked", "disrupted"} <= set(prof[0])
    assert prof[3]["status"] == "normal" and prof[16]["status"] == "congested"
    view = client.get("/api/lane-view?date=2031-03-12&hour=16").json()
    assert len(view["lanes"]) == 6 and all(l["status"] == "congested" or l["status"] == "busy" for l in view["lanes"])
    assert client.get("/api/lane-view?date=2031-03-12&hour=99").status_code == 422


def test_approval_endpoints_over_http(client):
    booking = {"truck_id": "TRK-APR1", "container_id": "CSQU3054383", "carrier": "Carrier-A", "cargo_category": "export",
               "container_type": "standard", "arrival_date": "2031-03-14", "arrival_hour": 11}
    one = client.post("/api/appointments", json=booking).json()["appointment"]
    two = client.post("/api/appointments", json={**booking, "truck_id": "TRK-APR2"}).json()["appointment"]
    assert one["status"] == "PENDING"
    assert client.post(f"/api/appointments/{one['id']}/approve").json()["status"] == "CONFIRMED"
    rejected = client.post(f"/api/appointments/{two['id']}/reject", json={"reason": "Over capacity"}).json()
    assert rejected["status"] == "REJECTED" and "Over capacity" in rejected["decision_reason"]
    assert client.post(f"/api/appointments/{two['id']}/approve").status_code == 422
    mine = client.get("/api/appointments?truck_id=trk-apr1").json()
    assert [a["id"] for a in mine] == [one["id"]]
    assert {a["status"] for a in client.get("/api/appointments?status=REJECTED,CONFIRMED").json()} <= {"REJECTED", "CONFIRMED"}
    assert client.post("/api/appointments/99999/approve").status_code == 422


def test_gate_change_and_live_endpoints_over_http(client):
    day = "2031-04-07"
    booking = {"truck_id": "TRK-LIVE1", "container_id": "CSQU3054383", "carrier": "Carrier-A", "cargo_category": "export",
               "container_type": "standard", "arrival_date": day, "arrival_hour": 10, "weather_severity": 0, "vessel_delay": False}
    appt = client.post("/api/appointments", json=booking).json()["appointment"]
    aid, lane = appt["id"], appt["lane"]
    slot_hour = int(appt["assigned_slot"][11:13])
    assert client.post(f"/api/appointments/{aid}/approve").status_code == 200
    try:
        live = client.get(f"/api/appointments/{aid}/live").json()
        assert live["phase"] == "upload_documents" and live["live"]["lane"] == lane
        assert live["live"]["delay_min"] == 0 and live["live"]["monitor"]["date"] == day

        closed = client.post(f"/api/lanes/{lane}/close", json={"hours": 2, "start": f"{day}T{slot_hour:02d}:00", "reason": "breakdown"})
        assert closed.status_code == 200 and closed.json()["lane_changes"][0]["appointment_id"] == aid
        assert client.get("/api/lanes/closures").json()[0]["reason"] == "breakdown"
        moved = client.get(f"/api/appointments/{aid}/live").json()
        assert moved["live"]["lane"] != lane and moved["notifications"][0]["type"] == "LANE_CHANGED"
        view = client.get(f"/api/lane-view?date={day}&hour={slot_hour}").json()
        assert view["lanes"][lane - 1]["status"] == "closed"
        notes = client.get(f"/api/appointments/{aid}/notifications").json()
        assert [n["type"] for n in notes][:2] == ["LANE_CHANGED", "APPROVED"]

        assert client.delete(f"/api/lanes/{lane}/close").json() == {"reopened": 1}
        assert client.post("/api/lanes/9/close", json={"hours": 2}).status_code == 422
        assert client.post("/api/lanes/2/close", json={"hours": 99}).status_code == 422

        out = client.post("/api/reoptimize", json={"queue_spike_pct": 200, "window_hours": 1, "start": f"{day}T{slot_hour:02d}:00",
                                                    "lane": moved["live"]["lane"]})
        assert out.status_code == 200 and out.json()["disruption"]["lane"] == moved["live"]["lane"]
        assert client.post("/api/reoptimize", json={"queue_spike_pct": 10, "lane": 9}).status_code == 422
        assert "lane_changes" in client.post("/api/rebalance").json()
    finally:
        for ln in range(1, 7):
            client.delete(f"/api/lanes/{ln}/close")
        client.delete("/api/disruption")
        client.post(f"/api/appointments/{aid}/cancel")


def test_live_endpoint_for_an_unknown_appointment(client):
    assert client.get("/api/appointments/987654/live").status_code == 422
    assert client.get("/api/appointments/987654/notifications").status_code == 422
