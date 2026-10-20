# Component 4 — Gate Appointment API

FastAPI service for the AI-Powered Gate Appointment System. Routes live in an
`APIRouter` (`router.py`) so the shared backend can mount them later; `main.py`
runs the component standalone.

## What it does
1. **Model 2** scores each booking: P(on time / late / no-show), with SHAP reasons (`noshow.py`).
2. **Overbooking rule** (`scheduler.py`): a slot may exceed capacity while *expected arrivals*
   (sum of 1 - no-show risk) stay within capacity, up to a hard cap (`GATE_MAX_OVERBOOK`).
3. **Model 1** forecasts every lane; the lowest-queue lane and the cheapest nearby slot are chosen.
4. **Clearance model** predicts time at the gate; the booking is saved with its reasons (`service.py`).
5. **Re-optimization**: after a vessel delay / queue spike only unconfirmed bookings are reshuffled with an
   integer program (PuLP/CBC); confirmed bookings stay fixed and every move is explained.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/appointments` | Score risk, pick slot (overbooking rule) and lane, predict clearance, save |
| GET | `/api/appointments?truck_id=&status=` | List saved appointments (a driver filters by truck) |
| GET | `/api/appointments/{id}/events` | Audit trail of assignments, moves and status changes |
| POST | `/api/appointments/{id}/approve` (`/confirm` alias) | Gate admin approves a PENDING request; this unlocks document upload |
| POST | `/api/appointments/{id}/reject` | Gate admin rejects with a reason `{reason}` |
| POST | `/api/appointments/{id}/cancel` | Driver or admin cancels (not once the truck is at the gate) |
| GET | `/api/gates/{lane}/desk?date=` | One gate officer's work list: approved trucks on that gate in slot order, counts, queue, closures |
| POST | `/api/appointments/{id}/check-in` | Officer: truck reached the gate (CONFIRMED -> ARRIVED) |
| POST | `/api/appointments/{id}/complete` | Officer: gate process complete (ARRIVED or CONFIRMED -> COMPLETED), records how long it took |
| POST | `/api/appointments/{id}/no-show` | Officer: truck never came (CONFIRMED -> NO_SHOW) |
| GET | `/api/appointments/{id}/live` | Driver's live trip: phase, next step, gate, lane status, queue, expected entry/wait, delay and why |
| GET | `/api/appointments/{id}/notifications` | Driver updates: approved/rejected, gate changed, delay update, documents checked |
| POST / DELETE | `/api/lanes/{lane}/close` | Close a lane for `hours` with a reason (bookings move automatically) / reopen it |
| GET | `/api/lanes/closures` | Active lane closures |
| POST | `/api/rebalance` | Move trucks from queued lanes to quieter ones at the same hour (min gain 3 trucks) |
| POST | `/api/reoptimize` | Apply a disruption (vessel delay hours, queue spike %, window, start) and re-optimize |
| DELETE | `/api/disruption` | Clear the active disruption |
| GET | `/api/slots?date=` | Hourly slot load: bookings, expected arrivals, capacity, forecast wait |
| GET | `/api/model-metrics` | Evaluation reports for the UI results page |
| POST | `/api/documents/check` | OCR one uploaded document (image/PDF): classify, extract fields, validate against the booking |
| GET | `/api/appointments/{id}/documents` | OCR verdicts recorded for an appointment |
| POST | `/api/appointments/{id}/documents/submit` | Count cleared vs missing/flagged documents and re-score no-show risk and clearance time |
| GET | `/api/documents/required?container_type=` | Required document slots for a container type |
| GET | `/api/documents/templates?container_type=` | What each document must contain (required and optional details) |
| GET | `/api/weather?date=` / `/api/carriers` / `/api/vessel-delay?vessel=&date=` | The derived conditions above |
| POST | `/api/assign-appointment` | Original single-shot lane+slot assignment (no persistence) |
| POST | `/api/predict-clearance` | Clearance-time model on its own |
| GET | `/api/congestion?at=` | Per-lane forecast queue and wait for a chosen hour |
| GET | `/api/congestion/profile?date=` | Forecast congestion for each of the 24 hours (worst-lane queue, wait, normal/busy/congested, bookings) |
| GET | `/api/lane-view?date=&hour=` | All 6 lanes at one hour: forecast queue, wait, status and the real appointments on each lane (applies any active disruption) |

## Approval workflow (driver and gate admin)
1. The driver checks the hourly gate status, picks an hour and requests an appointment. The request is saved as
   **PENDING** with a slot and gate already assigned (overbooking rule, lane choice).
2. A gate admin approves (**CONFIRMED**) or rejects (**REJECTED**, reason required). Until approved,
   `POST /api/appointments/{id}/documents/check` answers **409** - documents cannot be uploaded early.
3. After approval the driver uploads documents; each is OCR-checked and the booking is re-scored on submit.
4. On the day the gate officer opens the **Gate Desk**, chooses their gate, and for each truck presses *Check in* when it
   arrives and *Complete gate process* when it is released (or *No-show*). The driver sees each step on My Trip.
   A truck that has arrived still counts in its lane's queue and is never moved to another gate; completed and
   no-show trucks free the lane.
5. Until the slot time the driver follows `/live` and `/notifications`. When a disruption, a lane closure or a
   rebalance changes the expected wait by 5 min or more, or moves the truck to another gate, a notification with the
   reason is recorded (`DELAY_UPDATE` / `LANE_CHANGED`).

Roles in the front end are a **demo switch**, not authentication; drivers are identified by truck ID.

## Nothing about the booking's conditions is typed in
A booking only needs who, what and when (truck, container, carrier, cargo, arrival date and hour). Everything else
the models use is derived:

| Input | Source |
|---|---|
| Carrier reliability and past no-show rate | The carrier's history stored in the no-show model (`GET /api/carriers`) |
| Weather severity (0 clear .. 3 storm) | Live **Open-Meteo** forecast for the port on the arrival day (`weather.py`, `GET /api/weather?date=`); unavailable or beyond the 16-day range -> unknown, seasonal typical assumed |
| Linked vessel and its delay | Vessel name read from the booking confirmation by OCR, then looked up in the vessel schedule (`vessels.py`). Set `VESSEL_API_URL` to a Component 1 endpoint returning `{"delay_hours": n}` for `?vessel=&date=`; without it a labelled **simulated** schedule is used (`MV OCEAN PIONEER` 5 h, `MV PACIFIC STAR` 3 h, `MV EVER GRACE` on time, others ~12% delayed) |
| Customs risk and missing documents | OCR of the uploaded documents (below) |

Anything not yet known is stored as NULL and the risk model averages over the typical situation from the training
data, listing only what is actually known as the reasons. Explicit values can still be passed to the API for
simulations and tests.

## Customs risk and missing documents are derived, not typed
A booking is created without them (`POST /api/appointments` leaves `customs_risk_flag` / `missing_documents` out;
passing explicit values is still allowed for simulations). Until the documents are read:
- the no-show and clearance predictions are the **average over the typical document situation** from the training
  data (customs risk 72% low / 20% medium / 8% high; 75% / 15% / 7% / 3% for 0-3 missing documents), and
  the explanation lists only drivers that are actually known;
- the appointment stores both values as *unknown* (NULL), not as zero.

On submitting the documents (below) the OCR verdicts fix both: **missing documents** = required documents that are not
`cleared`, and **customs risk** = the CUSDEC's assessment (HS-chapter table: tobacco, alcohol, arms, explosives,
precious goods and art are high; fuels, chemicals, pharmaceuticals, machinery, electrical equipment and vehicles are
medium; other goods low; a missing HS code or declaration number raises the level). The table in
`documents.py` is illustrative; a real deployment would use the customs authority's own risk profile.
If no customs declaration was checked, customs risk stays unknown.

## Document templates: is the document complete? (`templates.py`)
Every document type has a **template**: the details it must contain, which are required or optional, and how each is
validated. After OCR extracts the details, the template gives a field-by-field checklist (ok / missing / invalid) and a
completeness score; a document is `cleared` only when every required detail is present and valid.

| Document | Required details (optional in brackets) |
|---|---|
| Booking confirmation | booking no., container, vessel, voyage, port of loading, port of discharge, sailing date (shipper, ETA, seal) |
| CUSDEC | declaration no., HS code, goods description, exporter, consignee, container, date (importer, vessel) |
| Gate pass | truck ID, container, valid-to not before the appointment date (valid-from not after it, appointment date, gate pass no., driver, vehicle registration) |
| VGM | container, weight 1,000-40,000 kg, ticked method 1 or 2, date of weighing (signatory, shipper) |
| Container and seal | container, seal number |
| Driver and vehicle | driver name, licence number, vehicle registration (licence expiry, which must not be before the appointment date; vehicle owner) |
| Special cargo | hazardous: container, UN number, IMDG class 1-9, packing group; reefer: container, set point -40 to 30 C (pre-trip inspection) |

Adding a document type or a required detail is one entry in `TEMPLATES`. Cross-checks against the booking (container
mismatch, wrong truck, wrong document type, low OCR quality) stay in `documents.validate`; completeness lives only in
the templates. `GET /api/documents/templates?container_type=` returns the templates for the UI, each upload returns its
`template` checklist, and the submission stores per-document completeness and the missing details.

## Reading real form layouts (`layout.py`)
Real terminal and shipping forms are grids: a label in one cell and its value in the cell beside or below it, a table
row of weights, a ticked check box, a numbered driving licence card. The OCR engine returns every cell as a text box
with a position, and `layout.py` reads those boxes:

- **Labels are matched loosely**: spaces, case, a field number (`13.`, `S.`) and OCR typos are ignored (`Vestel` is read
  as `Vessel`, `4.lmporter` as `Importer`).
- **A value is** the text after the label in the same box, else the next box on the same row, else the box(es) below it
  in the same column. A neighbour that is itself a label is never taken as a value, and a wrapped value stops when the
  text under it is not tight against it or is read with low confidence.
- **Repairs**: `2026-10-2106:00` is split into a date and a time; `SL1234S67` becomes `SL1234567`; `WPTRK-80579`
  becomes `WP TRK-80579`; `3.900` (a comma read as a full stop) becomes 3,900; `O0LU...` becomes `OOLU...` in the
  container owner code; a vessel read without spaces (`MAERSKCOLOMBO`) is restored to the known vessel name.
- **VGM table**: tare, cargo and gross mass are read from the container's row, and tare + cargo must equal the gross
  mass. **Check boxes**: of the two listed weighing methods, the one whose box has more ink is the ticked one; when it
  cannot be told, the method is reported missing instead of guessed.
- **Driving licence card**: the numbered fields (1 surname, 2 given names, 4b expiry, 5 licence number); the expiry must
  not be before the appointment date. If the surname's number was not read, the box above the given names is used.
- **Checks inside one document**: two different seal numbers (table vs photo), tare + cargo not equal to the gross
  mass, a gate pass for another day, a slot outside the pass's time window (warning).
- **Checks across documents** (`documents.cross_check`, shown as "please confirm" warnings on submit, never blocking):
  booking number, seal, vessel and voyage between the booking confirmation and the VGM / seal report / CUSDEC, and the
  driver on the gate pass against the driving licence.

Where the layout reader finds a value it overrides the plain-text patterns, which remain the fallback (digital PDFs
have no boxes). Names read without spaces stay as the OCR returned them.

## OCR document checking (`documents.py`)
Uploads are read with **RapidOCR** (ONNX, pip-only - no Tesseract install); digital PDFs use their text
layer, scanned PDFs are rendered then OCR'd. Each file then goes through:
1. **classify** into one of the 7 slots (booking confirmation, CUSDEC, gate pass, VGM, container/seal, driver and
   vehicle, special cargo) with weighted keywords (spaces are ignored, because photographed forms lose them);
2. **extract** container number (ISO 6346 check digit, O/0-style OCR repair), seal, VGM weight, booking no., truck,
   plate, licence, UN number, set-point temperature, dates;
3. **validate** against the booking: container must match, truck/date on the gate pass, VGM weight plausible
   (1,000-40,000 kg), seal present, UN number for hazardous, set point for reefer, wrong-slot detection, low
   OCR confidence -> `unreadable`;
4. **verdict**: `cleared` / `flagged` / `unreadable` with errors and warnings.

On **submit**, flagged or missing documents become the appointment's `missing_documents` count, no-show risk and
clearance time are re-scored by the models, the extracted fields are saved to `gate.gate_submissions`, and the
change is logged as a `DOCUMENTS_CHECKED` event. Files are processed in memory and never stored.

Demo files: `python tools/make_demo_appointments.py [--book --approve]` is the only document generator. It draws
the documents of three different appointments (clean standard, hazardous with a delayed vessel, reefer with high customs
scrutiny) in the layout of the real forms (`tools/real_format_documents.py`), plus faulty versions of some of them
(`<slot>__PROBLEM_<what>.png`), into the git-ignored `sample_documents/appointments/`. The tests build their documents
with the same generator (`tests/doc_fixtures.py`).

## Storage
By default bookings live in memory. To save them in the shared PostgreSQL database:
1. Apply `database/migrations/001_gate_appointment_predictions.sql` (additive; adds prediction columns,
   `gate.gate_appointment_events` and the six `GATE-n` lanes) and then `002_gate_appointment_conditions.sql`
   (weather and vessel-delay columns), `003_gate_appointment_auto_conditions.sql` (linked vessel and weather source;
   weather and vessel delay may be NULL).
2. Copy `.env.example` to `.env` and set `DATABASE_URL` (never commit `.env`).
`GET /` reports the active `storage` (`memory` or `postgresql`).

## Showing a busy gate without real data
The congestion numbers come from the trained SARIMAX models (quiet at night, busy from about 08:00, congested from about
10:00 to 18:00 with the peak around 16:00; "busy" = 4+ trucks queued in a lane, "congested" = 8+). To fill the gate with
realistic bookings so the lane monitor, slot board and optimizer have something to show:
```bash
python tools/seed_demo_bookings.py                  # 60 bookings for tomorrow, following the real hourly demand profile
python tools/seed_demo_bookings.py --count 150 --risky-share 0.4   # a packed day with unreliable-carrier bookings
```
The bookings go through `POST /api/appointments` like a driver's, so risk, overbooking and lane allocation all apply
(lanes are chosen by forecast queue plus trucks already booked on them, so a busy hour spreads across the gates). They
live in the running backend (restart it to clear them). Use `127.0.0.1`, not `localhost`, as the URL on Windows.

## Tests
```bash
python -m pytest tests -q                    # memory repository
TEST_DATABASE_URL=postgresql://... python -m pytest tests -q   # also runs the PostgreSQL contract tests
```

## Run
Full setup for a new computer, demo data and a walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md).

```bash
cd backend/gate
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```
Docs at `http://localhost:8000/docs`. Models are produced by `ml-models/gate/`.

## Known limits
- Forecast covers one week after the training cutoff; a chosen date maps onto it by hour-of-week.
- Wait time = forecast queue x 5.5 min (no separate model).
- OCR runs on clear scans and photos of printed text; handwriting and heavily degraded images are flagged as
  unreadable rather than guessed. Classification is keyword-based (no trained document classifier).
- Document verdicts are held in the running process until submitted (submission itself is saved).
- A disruption and lane closures are held in the running process (cleared by their DELETE endpoints or a restart).
- Closing a lane moves its trucks but does not reduce the hourly slot capacity.
- Approval and roles are not authenticated; the Driver / Gate admin switch is for demonstration.
- Slot capacity (`GATE_SLOT_CAPACITY`, default 6 for demos) is configurable; the evaluation uses 16.
